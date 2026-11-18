from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
PYTHON = Path(sys.executable)
MODEL_COPY_PATHS = (
    "claim.py",
    "pyproject.toml",
    "src",
    "knowledge",
    "schema",
    "ontology",
    "fixtures",
    "cases",
    "tests/admission_shim.py",
)
INSPECTOR_COPY_PATHS = (
    "scripts/run_case_based_inspection.py",
    "scripts/build_case_comparison.py",
    "scripts/investigate_total_loss_override.py",
    "scripts/inspection_provenance.py",
    "docs/case-reference-manifest-v1.json",
    "cases",
)


def _run(command: list[str], root: Path, **kwargs: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
        **kwargs,
    )


def _git(root: Path, *arguments: str) -> str:
    result = _run(["git", *arguments], root)
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def _copy_model_checkout(tmp_path: Path) -> Path:
    target = tmp_path / "selected-model"
    target.mkdir(parents=True)
    for relative in MODEL_COPY_PATHS:
        source = ROOT / relative
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(
                source,
                destination,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )
        else:
            shutil.copy2(source, destination)
    _git(target, "init", "--quiet")
    _git(target, "config", "user.email", "inspection-test@example.invalid")
    _git(target, "config", "user.name", "Inspection Test")
    _git(target, "add", ".")
    _git(target, "commit", "--quiet", "-m", "synthetic selected checkout")
    return target


def _copy_inspector_checkout(tmp_path: Path, marker: str = "") -> Path:
    target = tmp_path / "inspector"
    target.mkdir(parents=True)
    for relative in INSPECTOR_COPY_PATHS:
        source = ROOT / relative
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(
                source,
                destination,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )
        else:
            shutil.copy2(source, destination)
    if marker:
        (target / "inspector-marker.txt").write_text(marker + "\n", encoding="utf-8")
    _git(target, "init", "--quiet")
    _git(target, "config", "user.email", "inspection-test@example.invalid")
    _git(target, "config", "user.name", "Inspection Test")
    _git(target, "add", ".")
    _git(target, "commit", "--quiet", "-m", "synthetic inspector checkout")
    return target


@pytest.fixture(scope="module")
def valid_cross_checkout(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    temporary = tmp_path_factory.mktemp("valid-cross-checkout")
    model = _copy_model_checkout(temporary / "model")
    inspector = _copy_inspector_checkout(temporary / "inspector-a", "inspector-a")
    observation = temporary / "observation.json"
    comparison = temporary / "comparison.json"
    runner = _run(
        [
            str(PYTHON),
            str(inspector / "scripts" / "run_case_based_inspection.py"),
            "--root",
            str(model),
            "--cases",
            str(inspector / "cases"),
            "--internal",
            "--output",
            str(observation),
        ],
        inspector,
    )
    assert runner.returncode == 0, runner.stderr
    compared = _run(
        [
            str(PYTHON),
            str(inspector / "scripts" / "build_case_comparison.py"),
            str(observation),
            str(comparison),
            "--manifest",
            str(inspector / "docs" / "case-reference-manifest-v1.json"),
            "--cases",
            str(inspector / "cases"),
            "--model-root",
            str(model),
        ],
        inspector,
    )
    assert compared.returncode == 0, compared.stderr
    return {
        "temporary": temporary,
        "model": model,
        "inspector": inspector,
        "observation": observation,
        "comparison": comparison,
    }


def test_investigation_uses_selected_cross_checkout_despite_conflicting_pythonpath(
    tmp_path: Path,
) -> None:
    selected = _copy_model_checkout(tmp_path)
    inspector = _copy_inspector_checkout(tmp_path / "cross-inspector")
    output = tmp_path / "investigation.json"
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(ROOT / "src")
    result = _run(
        [
            str(PYTHON),
            str(inspector / "scripts" / "investigate_total_loss_override.py"),
            "--root",
            str(selected),
            "--cases",
            str(inspector / "cases"),
            "--manifest",
            str(inspector / "docs" / "case-reference-manifest-v1.json"),
            "--output",
            str(output),
        ],
        inspector,
        env=environment,
    )
    assert result.returncode == 0, result.stderr

    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["revision"] == _git(selected, "rev-parse", "HEAD")
    assert report["tree"] == _git(selected, "rev-parse", "HEAD^{tree}")
    expected_package = (selected / "src" / "iran_auto_claim").resolve()
    assert {
        "AuthorizationNotGranted",
        "Knowledge",
        "Review",
        "authorize_fixture_case",
        "compute",
    } <= set(report["import_origins"])
    for origin in report["import_origins"].values():
        assert expected_package in Path(origin).resolve().parents
        assert (ROOT / "src" / "iran_auto_claim").resolve() not in Path(
            origin
        ).resolve().parents


def test_runner_rejects_dirty_internal_probe_shim(tmp_path: Path) -> None:
    selected = _copy_model_checkout(tmp_path)
    inspector = _copy_inspector_checkout(tmp_path / "shim-inspector")
    shim = selected / "tests" / "admission_shim.py"
    shim.write_text(
        shim.read_text(encoding="utf-8")
        + "\n# uncommitted change that can influence internal probes\n",
        encoding="utf-8",
    )
    output = tmp_path / "observation.json"
    result = _run(
        [
            str(PYTHON),
            str(inspector / "scripts" / "run_case_based_inspection.py"),
            "--root",
            str(selected),
            "--cases",
            str(selected / "cases"),
            "--internal",
            "--output",
            str(output),
        ],
        inspector,
    )

    assert result.returncode != 0
    assert "tests/admission_shim.py" in result.stderr
    assert "uncommitted implementation inputs in checked scope" in result.stderr
    assert not output.exists()


def test_valid_cross_checkout_records_complete_evidence_contract(
    valid_cross_checkout: dict[str, Path],
) -> None:
    observation = json.loads(
        valid_cross_checkout["observation"].read_text(encoding="utf-8")
    )
    comparison = json.loads(
        valid_cross_checkout["comparison"].read_text(encoding="utf-8")
    )
    assert observation["case_inputs"]["count"] == 47
    assert len(observation["internal_test_direct"]) == 14
    assert observation["execution_profile"]["supported_review"]["acceptance_gate"]
    assert not observation["execution_profile"]["internal_test_direct"][
        "acceptance_gate"
    ]
    assert observation["inspector"]["harness_sha256"]
    assert comparison["derived_counts"] == {"KNOWN_DEVIATION": 10, "MATCH": 37}
    assert comparison["acceptance_gate_passed"] is True
    assert comparison["manifest"]["sha256"]
    assert comparison["manifest"]["known_deviation_envelope_sha256"]
    assert comparison["evidence_contract"]["internal_probe_evidence"] == {
        "present": True,
        "structurally_validated": True,
        "outcomes_validated_by_acceptance_gate": False,
        "role": "DIAGNOSTIC_NOT_OUTCOME_VALIDATED",
    }


def test_internal_probe_outcomes_are_explicitly_diagnostic_not_gated(
    tmp_path: Path, valid_cross_checkout: dict[str, Path]
) -> None:
    inspector = valid_cross_checkout["inspector"]
    observation = json.loads(
        valid_cross_checkout["observation"].read_text(encoding="utf-8")
    )
    observation["internal_test_direct"][0]["status"] = "SYNTHETIC_DIAGNOSTIC_DRIFT"
    changed_observation = tmp_path / "diagnostic-drift.json"
    changed_observation.write_text(
        json.dumps(observation, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    output = tmp_path / "diagnostic-comparison.json"
    result = _run(
        [
            str(PYTHON),
            str(inspector / "scripts" / "build_case_comparison.py"),
            str(changed_observation),
            str(output),
            "--manifest",
            str(inspector / "docs" / "case-reference-manifest-v1.json"),
            "--cases",
            str(inspector / "cases"),
            "--model-root",
            str(valid_cross_checkout["model"]),
        ],
        inspector,
    )
    assert result.returncode == 0, result.stderr
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["acceptance_gate_passed"] is True
    assert report["evidence_contract"]["internal_probe_evidence"][
        "outcomes_validated_by_acceptance_gate"
    ] is False


def test_investigation_rejects_modified_external_c104(
    tmp_path: Path, valid_cross_checkout: dict[str, Path]
) -> None:
    inspector = valid_cross_checkout["inspector"]
    external_cases = tmp_path / "external-cases"
    shutil.copytree(inspector / "cases", external_cases)
    c104 = external_cases / "inspection-c104-theft-60-59-clock.json"
    payload = json.loads(c104.read_text(encoding="utf-8"))
    payload["answers"]["Q-S2-12"] = "1404-06-17"
    c104.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    output = tmp_path / "investigation.json"
    result = _run(
        [
            str(PYTHON),
            str(inspector / "scripts" / "investigate_total_loss_override.py"),
            "--root",
            str(valid_cross_checkout["model"]),
            "--cases",
            str(external_cases),
            "--manifest",
            str(inspector / "docs" / "case-reference-manifest-v1.json"),
            "--output",
            str(output),
        ],
        inspector,
    )
    assert result.returncode != 0
    assert "C104 input digest differs from the reference manifest" in result.stderr
    assert not output.exists()


def test_runner_rejects_mutated_caller_probe_definition(
    tmp_path: Path, valid_cross_checkout: dict[str, Path]
) -> None:
    inspector = _copy_inspector_checkout(tmp_path / "dirty-inspector")
    runner_path = inspector / "scripts" / "run_case_based_inspection.py"
    source = runner_path.read_text(encoding="utf-8")
    runner_path.write_text(
        source.replace("INT-01 rescue omitted", "INT-01 MUTATED CALLER HARNESS", 1),
        encoding="utf-8",
    )
    output = tmp_path / "dirty-harness-observation.json"
    result = _run(
        [
            str(PYTHON),
            str(runner_path),
            "--root",
            str(valid_cross_checkout["model"]),
            "--cases",
            str(inspector / "cases"),
            "--internal",
            "--output",
            str(output),
        ],
        inspector,
    )
    assert result.returncode != 0
    assert "uncommitted executable inputs" in result.stderr
    assert not output.exists()


def test_comparator_rejects_stale_clean_inspector_revision(
    tmp_path: Path, valid_cross_checkout: dict[str, Path]
) -> None:
    stale = _copy_inspector_checkout(tmp_path / "stale-inspector", "stale-revision")
    output = tmp_path / "stale-comparison.json"
    result = _run(
        [
            str(PYTHON),
            str(stale / "scripts" / "build_case_comparison.py"),
            str(valid_cross_checkout["observation"]),
            str(output),
            "--manifest",
            str(stale / "docs" / "case-reference-manifest-v1.json"),
            "--cases",
            str(stale / "cases"),
            "--model-root",
            str(valid_cross_checkout["model"]),
        ],
        stale,
    )
    assert result.returncode == 2
    assert "stale or unauthorized inspection harness" in result.stderr
    assert not output.exists()


def test_comparator_rejects_different_committed_unauthorized_harness(
    tmp_path: Path, valid_cross_checkout: dict[str, Path]
) -> None:
    unauthorized = _copy_inspector_checkout(
        tmp_path / "unauthorized-inspector", "unauthorized-harness"
    )
    runner_path = unauthorized / "scripts" / "run_case_based_inspection.py"
    source = runner_path.read_text(encoding="utf-8")
    runner_path.write_text(
        source.replace("INT-01 rescue omitted", "INT-01 UNAUTHORIZED HARNESS", 1),
        encoding="utf-8",
    )
    _git(unauthorized, "add", "scripts/run_case_based_inspection.py")
    _git(unauthorized, "commit", "--quiet", "-m", "mutate probe harness")
    output = tmp_path / "unauthorized-comparison.json"
    result = _run(
        [
            str(PYTHON),
            str(unauthorized / "scripts" / "build_case_comparison.py"),
            str(valid_cross_checkout["observation"]),
            str(output),
            "--manifest",
            str(unauthorized / "docs" / "case-reference-manifest-v1.json"),
            "--cases",
            str(unauthorized / "cases"),
            "--model-root",
            str(valid_cross_checkout["model"]),
        ],
        unauthorized,
    )
    assert result.returncode == 2
    assert "stale or unauthorized inspection harness" in result.stderr
    assert not output.exists()
