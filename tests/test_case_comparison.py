from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from scripts import build_case_comparison as comparator
from scripts import run_case_based_inspection as inspection


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs" / "case-reference-manifest-v1.json"


def _case_hashes() -> dict[str, str]:
    return {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted((ROOT / "cases").glob("inspection-*.json"))
    }


@pytest.fixture(autouse=True)
def inspection_cases_remain_unchanged() -> None:
    before = _case_hashes()
    yield
    assert _case_hashes() == before
    result = subprocess.run(
        ["git", "diff", "--quiet", "--", "cases"], cwd=ROOT, check=False
    )
    assert result.returncode == 0


@pytest.fixture(scope="module")
def baseline_observation() -> dict[str, object]:
    return {
        "revision": "TEST",
        "tree": "TEST",
        "python": "3.11",
        "supported_path": inspection._supported_cases(ROOT, ROOT / "cases"),
    }


def _copy_cases(tmp_path: Path) -> Path:
    target = tmp_path / "cases"
    shutil.copytree(ROOT / "cases", target)
    return target


def _write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _mutated_case_report(
    tmp_path: Path,
    baseline_observation: dict[str, object],
    case_id: str,
    mutate,
) -> tuple[dict[str, object], dict[str, object]]:
    case_root = _copy_cases(tmp_path)
    case_path = case_root / f"{case_id}.json"
    payload = json.loads(case_path.read_text(encoding="utf-8"))
    mutate(payload)
    _write_json(case_path, payload)

    observation = copy.deepcopy(baseline_observation)
    rows = observation["supported_path"]
    assert isinstance(rows, list)
    replacement = inspection._supported_case(ROOT, case_path)
    rows[:] = [replacement if row["case"] == case_id else row for row in rows]
    observation_path = tmp_path / "observation.json"
    _write_json(observation_path, observation)

    report, passed = comparator.compare(MANIFEST, observation_path, case_root)
    result = next(row for row in report["cases"] if row["case_id"] == case_id)
    assert not passed
    assert result["comparison_verdict"] == "MISMATCH"
    return result, replacement


def _failure_paths(result: dict[str, object]) -> set[str]:
    failures = result["reference_assertion_failures"]
    assert isinstance(failures, list)
    return {failure["path"] for failure in failures}


def test_c42_rescue_100_to_101_crosses_strict_threshold(
    tmp_path: Path, baseline_observation: dict[str, object]
) -> None:
    result, observed = _mutated_case_report(
        tmp_path,
        baseline_observation,
        "inspection-c42-at-7500",
        lambda payload: payload["answers"].__setitem__("Q-S4-07", 101),
    )
    assert observed["review_branch"] == "TOTAL_LOSS"
    assert observed["authorization"]["granted"] is False
    assert {"input_sha256", "classification", "authorization.granted"} <= _failure_paths(result)


def test_c45_omitted_rescue_to_explicit_zero_is_detected(
    tmp_path: Path, baseline_observation: dict[str, object]
) -> None:
    result, observed = _mutated_case_report(
        tmp_path,
        baseline_observation,
        "inspection-c45-rescue-omitted",
        lambda payload: payload["answers"].__setitem__("Q-S4-07", 0),
    )
    assert observed["authorization"]["granted"] is True
    assert "authorization.granted" in _failure_paths(result)


def test_authorization_granted_to_refused_is_detected(
    tmp_path: Path, baseline_observation: dict[str, object]
) -> None:
    result, observed = _mutated_case_report(
        tmp_path,
        baseline_observation,
        "inspection-c42-at-7500",
        lambda payload: payload["answers"].__setitem__("Q-S3-01", "WRONG_CLASS"),
    )
    assert observed["decision"] == "REFUSE"
    assert observed["authorization"]["granted"] is False
    assert {"review_decision", "authorization.granted"} <= _failure_paths(result)


def test_payable_change_with_same_branch_is_detected(
    tmp_path: Path, baseline_observation: dict[str, object]
) -> None:
    result, observed = _mutated_case_report(
        tmp_path,
        baseline_observation,
        "inspection-c42-at-7500",
        lambda payload: payload["answers"].__setitem__("Q-S4-07", 99),
    )
    assert observed["review_branch"] == "PARTIAL_DAMAGE"
    assert observed["payable_irr"] == 6759
    paths = _failure_paths(result)
    assert "classification" not in paths
    assert "calculation.payable_irr" in paths


def test_changed_input_digest_without_output_change_is_detected(
    tmp_path: Path, baseline_observation: dict[str, object]
) -> None:
    original = next(
        row
        for row in baseline_observation["supported_path"]
        if row["case"] == "inspection-c42-at-7500"
    )
    result, observed = _mutated_case_report(
        tmp_path,
        baseline_observation,
        "inspection-c42-at-7500",
        lambda payload: payload.__setitem__("note", payload["note"] + " digest-only"),
    )
    for key in ("decision", "review_branch", "status", "payable_irr"):
        assert observed[key] == original[key]
    assert "input_sha256" in _failure_paths(result)


def test_missing_and_duplicate_case_are_rejected(
    tmp_path: Path, baseline_observation: dict[str, object]
) -> None:
    case_root = _copy_cases(tmp_path)
    missing = copy.deepcopy(baseline_observation)
    missing["supported_path"].pop()
    missing_path = tmp_path / "missing.json"
    _write_json(missing_path, missing)
    with pytest.raises(comparator.ManifestError, match="case-set mismatch"):
        comparator.compare(MANIFEST, missing_path, case_root)

    duplicate = copy.deepcopy(baseline_observation)
    duplicate["supported_path"].append(copy.deepcopy(duplicate["supported_path"][0]))
    duplicate_path = tmp_path / "duplicate.json"
    _write_json(duplicate_path, duplicate)
    with pytest.raises(comparator.ManifestError, match="duplicate observation cases"):
        comparator.compare(MANIFEST, duplicate_path, case_root)


def test_changed_material_trace_assertion_is_detected(
    tmp_path: Path, baseline_observation: dict[str, object]
) -> None:
    result, observed = _mutated_case_report(
        tmp_path,
        baseline_observation,
        "inspection-c105-theft-59-days",
        lambda payload: payload["answers"].__setitem__(
            "Q-S2-14", "synthetic alternative clock-source record"
        ),
    )
    assert observed["review_branch"] == "THEFT"
    assert observed["status"] == "PENDING_60_DAY_CRITERION"
    assert observed["payable_irr"] is None
    assert "fields.theft_clock.source" in _failure_paths(result)


def test_manifest_rejects_duplicate_id_and_float_money(tmp_path: Path) -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    manifest["cases"].append(copy.deepcopy(manifest["cases"][0]))
    duplicate_path = tmp_path / "duplicate-manifest.json"
    _write_json(duplicate_path, manifest)
    with pytest.raises(comparator.ManifestError, match="duplicate manifest cases"):
        comparator.load_manifest(duplicate_path)

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    manifest["cases"][0]["expected"]["calculation"]["payable_irr"] = 1.5
    malformed_path = tmp_path / "float-money.json"
    _write_json(malformed_path, manifest)
    with pytest.raises(comparator.ManifestError, match="not an integer IRR amount"):
        comparator.load_manifest(malformed_path)


def test_cli_exits_nonzero_for_new_mismatch(
    tmp_path: Path, baseline_observation: dict[str, object]
) -> None:
    observation = copy.deepcopy(baseline_observation)
    row = next(
        item
        for item in observation["supported_path"]
        if item["case"] == "inspection-c42-at-7500"
    )
    row["payable_irr"] = 1
    observation_path = tmp_path / "mismatch.json"
    output_path = tmp_path / "comparison.json"
    _write_json(observation_path, observation)
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_case_comparison.py"),
            str(observation_path),
            str(output_path),
            "--manifest",
            str(MANIFEST),
            "--cases",
            str(ROOT / "cases"),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 1
    assert json.loads(output_path.read_text(encoding="utf-8"))["acceptance_gate_passed"] is False
