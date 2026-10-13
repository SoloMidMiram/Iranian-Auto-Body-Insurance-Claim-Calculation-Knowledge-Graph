"""Shared fail-closed provenance helpers for inspection tooling."""

from __future__ import annotations

import importlib
import importlib.util
import inspect
import os
from pathlib import Path
import re
import subprocess
import sys
from types import ModuleType
from typing import Any, Iterable


BASE_MODEL_PATHS = (
    "claim.py",
    "pyproject.toml",
    "src",
    "knowledge",
    "schema",
    "ontology",
    "fixtures",
)
INTERNAL_PROBE_PATHS = ("tests/admission_shim.py",)
INTERNAL_PROBE_ORIGINS_RELATIVE = {
    "iran_auto_claim": "src/iran_auto_claim/__init__.py",
    "iran_auto_claim.knowledge": "src/iran_auto_claim/knowledge.py",
    "tests.admission_shim": "tests/admission_shim.py",
    "tests.admission_shim.compute": "tests/admission_shim.py",
    "tests.admission_shim.compute_authorized": "src/iran_auto_claim/engine.py",
    "tests.admission_shim._authorize_fixture_case": "src/iran_auto_claim/fixtures.py",
}
GIT_OBJECT_ID = re.compile(r"[0-9a-f]{40,64}")


class ProvenanceError(RuntimeError):
    """The selected checkout cannot support a trustworthy observation."""


def model_scope(include_internal_probes: bool) -> tuple[str, ...]:
    """Return the exact checked-input scope for an observation profile."""

    if include_internal_probes:
        return BASE_MODEL_PATHS + INTERNAL_PROBE_PATHS
    return BASE_MODEL_PATHS


def isolated_environment(root: Path) -> dict[str, str]:
    """Build an environment that cannot inherit a competing model checkout."""

    environment = dict(os.environ)
    environment["PYTHONPATH"] = str((root.resolve() / "src").resolve())
    environment["PYTHONNOUSERSITE"] = "1"
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return environment


def _git(root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise ProvenanceError(
            f"cannot inspect selected checkout with git {' '.join(arguments)}: {detail}"
        )
    return result.stdout.strip()


def model_identity(root: Path, scope: Iterable[str]) -> tuple[str, str]:
    """Return revision/tree only for a clean, exact worktree and input scope."""

    selected = root.resolve()
    top = Path(_git(selected, "rev-parse", "--show-toplevel")).resolve()
    if top != selected:
        raise ProvenanceError(
            f"model root must be the git worktree root: expected {top}, got {selected}"
        )
    paths = tuple(scope)
    dirty = _git(
        selected,
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
        "--",
        *paths,
    )
    if dirty:
        raise ProvenanceError(
            "model checkout has uncommitted implementation inputs in checked scope: "
            f"{dirty.splitlines()}"
        )
    revision = _git(selected, "rev-parse", "HEAD")
    tree = _git(selected, "rev-parse", "HEAD^{tree}")
    if not GIT_OBJECT_ID.fullmatch(revision) or not GIT_OBJECT_ID.fullmatch(tree):
        raise ProvenanceError(
            "model revision and tree must be full lowercase git object IDs"
        )
    return revision, tree


def _expected_package_root(root: Path) -> Path:
    return (root.resolve() / "src" / "iran_auto_claim").resolve()


def verify_module_origin(root: Path, module: ModuleType, label: str) -> str:
    """Return an origin only when a module came from the selected checkout."""

    raw_origin = getattr(module, "__file__", None)
    if not isinstance(raw_origin, str):
        raise ProvenanceError(f"{label} has no filesystem import origin")
    origin = Path(raw_origin).resolve()
    expected = _expected_package_root(root)
    if origin != expected and expected not in origin.parents:
        raise ProvenanceError(
            f"{label} resolved outside the selected model package {expected}: {origin}"
        )
    return str(origin)


def verify_object_origin(root: Path, value: Any, label: str) -> str:
    """Verify the defining module for a class or callable."""

    module = inspect.getmodule(value)
    if module is None:
        raise ProvenanceError(f"cannot determine defining module for {label}")
    return verify_module_origin(root, module, label)


def verify_object_file(value: Any, expected_path: Path, label: str) -> str:
    """Verify that a helper is defined by one exact selected repository file."""

    module = inspect.getmodule(value)
    raw_origin = None if module is None else getattr(module, "__file__", None)
    if not isinstance(raw_origin, str):
        raise ProvenanceError(f"{label} has no filesystem import origin")
    origin = Path(raw_origin).resolve()
    expected = expected_path.resolve()
    if origin != expected:
        raise ProvenanceError(
            f"{label} resolved outside the selected helper file {expected}: {origin}"
        )
    return str(origin)


def load_model_modules(
    root: Path, names: Iterable[str]
) -> tuple[dict[str, ModuleType], dict[str, str]]:
    """Import selected model modules after removing cached competing imports."""

    selected = root.resolve()
    sys.dont_write_bytecode = True
    root_src = str((selected / "src").resolve())
    root_text = str(selected)
    remaining = [
        entry for entry in sys.path if entry not in {root_src, root_text}
    ]
    sys.path[:] = [root_src, root_text, *remaining]
    for module_name in tuple(sys.modules):
        if module_name == "iran_auto_claim" or module_name.startswith(
            "iran_auto_claim."
        ):
            del sys.modules[module_name]
    importlib.invalidate_caches()

    requested = tuple(names)
    modules = {
        name: importlib.import_module(f"iran_auto_claim.{name}") for name in requested
    }
    package = importlib.import_module("iran_auto_claim")
    origins = {"iran_auto_claim": verify_module_origin(selected, package, "package")}
    for name, module in modules.items():
        origins[f"iran_auto_claim.{name}"] = verify_module_origin(
            selected, module, f"module iran_auto_claim.{name}"
        )
    return modules, origins


def load_selected_file(root: Path, relative_path: str, module_name: str) -> ModuleType:
    """Load a repository helper by exact path, never by ambient package lookup."""

    selected = root.resolve()
    path = (selected / relative_path).resolve()
    if selected not in path.parents:
        raise ProvenanceError(f"selected helper escapes model root: {path}")
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ProvenanceError(f"cannot create import specification for {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    origin = Path(getattr(module, "__file__", "")).resolve()
    if origin != path:
        raise ProvenanceError(
            f"selected helper origin differs from requested file: {origin} != {path}"
        )
    return module
