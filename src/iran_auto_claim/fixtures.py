"""Fixture corpus runner: the P01-L50 validation suite.

The fixtures are the contract. The harness is deliberately strict: an expected
key it cannot resolve is reported as MISSING rather than skipped, so a fixture
can never pass by having nothing to check.

Key resolution, in order:

* ``payable`` and its synonyms  -> the single payable
* ``scenario_*``                -> the corresponding scenario in the scenario set
* ``status`` / ``reason`` / ``route`` -> the matching result attribute, exactly
* ``guard`` / ``flag`` / ``franchise`` -> membership in the emitted label set
* anything else                 -> a named intermediate in result.fields
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from .engine import CalcResult, compute
from .knowledge import DEFAULT_ROOT, Knowledge
from .money import D

FIXTURE_PATH = DEFAULT_ROOT / "fixtures" / "cases.json"

PAYABLE_KEYS = {
    "payable",
    "payable_if_no_further_deduction",
    "payable_if_no_other_deductions",
    "payable_if_fully_insured",
    "insurer_payable",
    "payable_or_recovery_amount",
    "third_party",
}

SCENARIO_KEYS = {
    "scenario_ratio_then_franchise": 0,
    "scenario_franchise_then_ratio": 1,
}

EXACT_ATTR_KEYS = {"status": "status", "reason": "reason", "route": "route"}

LABEL_KEYS = {"guard", "flag", "franchise"}


def load_fixtures(path: Path | str | None = None) -> list[dict[str, Any]]:
    target = Path(path) if path else FIXTURE_PATH
    payload = json.loads(target.read_text(encoding="utf-8"))
    return payload["cases"]


def _equal(expected: Any, actual: Any) -> bool:
    if expected is None:
        return actual is None
    if actual is None:
        return False
    if isinstance(actual, bool):
        return bool(expected) is actual
    if isinstance(actual, Decimal):
        try:
            return D(expected) == actual
        except Exception:
            return False
    if isinstance(actual, str):
        return str(expected) == actual
    return expected == actual


def check_expectations(expected: dict[str, Any], result: CalcResult) -> list[str]:
    """Return a list of human-readable mismatches. Empty means the fixture passed."""
    problems: list[str] = []

    for key, wanted in expected.items():
        if key in PAYABLE_KEYS:
            if not _equal(wanted, result.payable):
                problems.append(f"payable: expected {wanted!r}, got {result.payable!r}")
            continue

        if key in SCENARIO_KEYS:
            index = SCENARIO_KEYS[key]
            actual = (
                result.payable_scenarios[index]
                if len(result.payable_scenarios) > index
                else None
            )
            if not _equal(wanted, actual):
                problems.append(f"{key}: expected {wanted!r}, got {actual!r}")
            continue

        if key in EXACT_ATTR_KEYS:
            actual = getattr(result, EXACT_ATTR_KEYS[key])
            if str(wanted) != (str(actual) if actual is not None else ""):
                problems.append(f"{key}: expected {wanted!r}, got {actual!r}")
            continue

        if key in LABEL_KEYS:
            if str(wanted) not in result.labels:
                problems.append(
                    f"{key}: expected label {wanted!r}, emitted {sorted(result.labels)}"
                )
            continue

        if key in result.fields:
            actual = result.fields[key]
            if not _equal(wanted, actual):
                problems.append(f"{key}: expected {wanted!r}, got {actual!r}")
            continue

        problems.append(f"{key}: UNRESOLVED expectation key (engine reports no such field)")

    return problems


def evaluate_fixture(fixture: dict[str, Any], kb: Knowledge) -> tuple[CalcResult, list[str]]:
    case_payload = {
        "claim_id": fixture["id"],
        "unit": fixture.get("unit", "million_toman"),
        "classification": {
            "branch": fixture["branch"],
            "domain": _domain_for(fixture["branch"]),
        },
        "damage": fixture.get("inputs", {}),
    }
    result = compute(case_payload, kb)
    return result, check_expectations(fixture.get("expected", {}), result)


def _domain_for(branch: str) -> str:
    from .case import BRANCH_ALIASES, DOMAIN_BY_BRANCH

    canonical = BRANCH_ALIASES.get(branch, {}).get("branch", branch)
    return DOMAIN_BY_BRANCH.get(canonical, "BODY")


def run_all(kb: Knowledge | None = None, path: Path | str | None = None) -> list[dict[str, Any]]:
    kb = kb or Knowledge.load()
    report: list[dict[str, Any]] = []
    for fixture in load_fixtures(path):
        result, problems = evaluate_fixture(fixture, kb)
        report.append(
            {
                "id": fixture["id"],
                "branch": fixture["branch"],
                "ok": not problems,
                "problems": problems,
                "payable": result.payable,
                "payable_scenarios": list(result.payable_scenarios),
                "status": result.status,
                "reason": result.reason,
                "labels": sorted(result.labels),
                "confidence": result.formula_confidence,
                "result": result,
            }
        )
    return report
