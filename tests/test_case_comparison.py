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
from scripts import inspection_provenance as provenance
from scripts import run_case_based_inspection as inspection


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs" / "case-reference-manifest-v1.json"


def _manifest_cases() -> dict[str, dict[str, object]]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return {case["case_id"]: case for case in manifest["cases"]}


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
        "revision": inspection._git_value(ROOT, "HEAD"),
        "tree": inspection._git_value(ROOT, "HEAD^{tree}"),
        "python": "3.11",
        "import_origin_relative": "src/iran_auto_claim/__init__.py",
        "provenance_profile": "SUPPORTED_ONLY",
        "model_scope": list(comparator.MODEL_PATHS),
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


def _git(root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=root,
        text=True,
        capture_output=True,
        check=True,
    )
    return result.stdout.strip()


def test_internal_observation_requires_internal_probe_scope(
    tmp_path: Path, baseline_observation: dict[str, object]
) -> None:
    observation = copy.deepcopy(baseline_observation)
    observation["internal_test_direct"] = []
    observation["provenance_profile"] = "SUPPORTED_PLUS_INTERNAL"
    observation_path = tmp_path / "observation.json"
    _write_json(observation_path, observation)

    with pytest.raises(comparator.ManifestError, match="model_scope"):
        comparator.compare(MANIFEST, observation_path, ROOT / "cases")


def test_internal_observation_requires_verified_internal_import_origins(
    tmp_path: Path, baseline_observation: dict[str, object]
) -> None:
    observation = copy.deepcopy(baseline_observation)
    observation["internal_test_direct"] = []
    observation["provenance_profile"] = "SUPPORTED_PLUS_INTERNAL"
    observation["model_scope"] = list(provenance.model_scope(True))
    observation_path = tmp_path / "observation.json"
    _write_json(observation_path, observation)

    with pytest.raises(comparator.ManifestError, match="internal probe import origins"):
        comparator.compare(MANIFEST, observation_path, ROOT / "cases")


def test_reference_locators_are_case_relevant() -> None:
    cases = _manifest_cases()

    glass = cases["inspection-c102-glass-endorsement-token-only"]["reference"]
    assert {
        "REG53_ART5_ENDORSABLE_EXCLUSIONS",
        "U03_GLASS_ONLY_ENDORSEMENT_WORDING",
        "U11_GLASS_ARTICLE10_EXEMPTION",
    } <= set(" ".join(glass["rule_locators"]).replace("/", " ").split())

    intensified = cases["inspection-c81-risk-intensified-yes"]["reference"]
    assert "U15_RISK_INTENSIFICATION_PREMIUM_RATIO" in intensified["rule_locators"]

    overdue = cases["inspection-c83-instalment-overdue"]["reference"]
    assert "POLICY_CANCELLATION_STATUS_UNRESOLVED" in overdue["rule_locators"]

    for reference in (glass, intensified, overdue):
        assert "REG53_POLICY_DEFINED_FRANCHISE" not in reference["rule_locators"]
        assert "U02_FRANCHISE_BASE_SCHEDULES" not in reference["rule_locators"]

    late_notice = cases["inspection-c97-late-notice-no-excuse"]["reference"]
    assert "REG53_NOTICE_AND_DUTIES" in late_notice["rule_locators"]
    assert "REG53_ART14_SUBROGATION" not in late_notice["rule_locators"]

    recourse = cases["inspection-c98-recourse-released"]["reference"]
    assert "REG53_ART14_SUBROGATION" in recourse["rule_locators"]
    assert "REG53_NOTICE_AND_DUTIES" not in recourse["rule_locators"]

    overinsured = cases["inspection-c73-overinsured"]["reference"]
    assert "U01_ARTICLE10_PARTIAL_ORDER" not in overinsured["rule_locators"]

    total_loss = cases["inspection-c74-underinsured-total-loss"]["reference"]
    assert "REG53_ART19_TOTAL_LOSS_NO_DOUBLE_UNDERINSURANCE" in total_loss[
        "rule_locators"
    ]


def test_manifest_source_ids_resolve_to_registered_sources() -> None:
    sources = json.loads(
        (ROOT / "knowledge" / "sources.json").read_text(encoding="utf-8")
    )
    registered = {source["node_id"] for source in sources["sources"]}
    for case_id, case in _manifest_cases().items():
        unknown = set(case["reference"]["source_ids"]) - registered
        assert not unknown, f"{case_id} has unregistered source IDs: {sorted(unknown)}"


def test_model_change_with_unchanged_case_hashes_rejects_stale_observation(
    tmp_path: Path, baseline_observation: dict[str, object]
) -> None:
    model_root = tmp_path / "model"
    case_root = model_root / "cases"
    shutil.copytree(ROOT / "cases", case_root)
    model_file = model_root / "src" / "iran_auto_claim" / "model_probe.py"
    model_file.parent.mkdir(parents=True)
    model_file.write_text("MODEL_VERSION = 1\n", encoding="utf-8")
    (model_root / "claim.py").write_text(
        "# synthetic model entry point\n", encoding="utf-8"
    )
    _git(model_root, "init", "-b", "main")
    _git(model_root, "add", "claim.py", "src", "cases")
    _git(
        model_root,
        "-c",
        "user.name=PR57 Test",
        "-c",
        "user.email=pr57@example.invalid",
        "commit",
        "-m",
        "model v1",
    )

    observation = copy.deepcopy(baseline_observation)
    observation["revision"] = _git(model_root, "rev-parse", "HEAD")
    observation["tree"] = _git(model_root, "rev-parse", "HEAD^{tree}")
    observation_path = tmp_path / "stale-model-observation.json"
    _write_json(observation_path, observation)
    before = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in case_root.glob("inspection-*.json")
    }

    model_file.write_text("MODEL_VERSION = 2\n", encoding="utf-8")
    after = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in case_root.glob("inspection-*.json")
    }
    assert after == before
    with pytest.raises(
        comparator.ManifestError, match="uncommitted implementation inputs"
    ):
        comparator.compare(
            MANIFEST,
            observation_path,
            case_root,
            model_root=model_root,
        )

    _git(model_root, "add", str(model_file.relative_to(model_root)))
    _git(
        model_root,
        "-c",
        "user.name=PR57 Test",
        "-c",
        "user.email=pr57@example.invalid",
        "commit",
        "-m",
        "model v2",
    )
    assert {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in case_root.glob("inspection-*.json")
    } == before
    with pytest.raises(comparator.ManifestError, match="observation revision mismatch"):
        comparator.compare(
            MANIFEST,
            observation_path,
            case_root,
            model_root=model_root,
        )


@pytest.mark.parametrize(
    ("old", "new"),
    [("143.20", "143.21"), ("m-toman", "IRR")],
    ids=("rendered-amount", "rendered-unit"),
)
def test_standalone_calc_rendered_money_and_unit_are_enforced(
    tmp_path: Path,
    baseline_observation: dict[str, object],
    old: str,
    new: str,
) -> None:
    observation = copy.deepcopy(baseline_observation)
    row = next(
        item
        for item in observation["supported_path"]
        if item["case"] == "inspection-c13d-replacement-control"
    )
    payable_line = next(
        line
        for line in row["calc_stdout"].splitlines()
        if line.lstrip().startswith("PAYABLE:")
    )
    changed_line = payable_line.replace(old, new, 1)
    assert changed_line != payable_line
    row["calc_stdout"] = row["calc_stdout"].replace(payable_line, changed_line, 1)
    observation_path = tmp_path / f"standalone-{new}.json"
    _write_json(observation_path, observation)

    report, passed = comparator.compare(MANIFEST, observation_path, ROOT / "cases")
    result = next(
        item
        for item in report["cases"]
        if item["case_id"] == "inspection-c13d-replacement-control"
    )
    assert not passed
    assert result["comparison_verdict"] == "MISMATCH"
    assert "standalone_calculation.payable_rendered" in _failure_paths(result)
    evidence = result["observed_behavior"]["standalone_calculation"]
    assert evidence["expected_payable"] == "143.20 m-toman"
    assert evidence["observed_payable"] == changed_line.split("PAYABLE:", 1)[1].strip()
    assert evidence["display_unit"] == "million_toman"
    assert evidence["irr_per_display_unit"] == 10_000_000


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
