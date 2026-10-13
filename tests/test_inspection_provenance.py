from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


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
    target.mkdir()
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


def test_investigation_uses_selected_cross_checkout_despite_conflicting_pythonpath(
    tmp_path: Path,
) -> None:
    selected = _copy_model_checkout(tmp_path)
    output = tmp_path / "investigation.json"
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(ROOT / "src")
    result = _run(
        [
            str(PYTHON),
            str(ROOT / "scripts" / "investigate_total_loss_override.py"),
            "--root",
            str(selected),
            "--cases",
            "cases",
            "--output",
            str(output),
        ],
        ROOT,
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
            str(ROOT / "scripts" / "run_case_based_inspection.py"),
            "--root",
            str(selected),
            "--cases",
            str(selected / "cases"),
            "--internal",
            "--output",
            str(output),
        ],
        ROOT,
    )

    assert result.returncode != 0
    assert "tests/admission_shim.py" in result.stderr
    assert "uncommitted implementation inputs in checked scope" in result.stderr
    assert not output.exists()
