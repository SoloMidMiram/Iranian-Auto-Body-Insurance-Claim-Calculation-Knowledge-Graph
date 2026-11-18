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

import copy
import hashlib
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from .admission import CalculationAuthorization, _internal_test_direct_authorize
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


def _authorize_fixture_case(
    case_payload: dict[str, Any],
    kb: Knowledge,
    *,
    decision: str = "COMPUTE",
) -> CalculationAuthorization:
    """Use the visibly non-production path for the authored fixture corpus."""
    del kb  # kept in the signature for the existing fixture/test harness
    return _internal_test_direct_authorize(
        _with_synthetic_authority(case_payload),
        decision=decision,
        purpose="P01-L50_SYNTHETIC_FIXTURE",
    )


def _with_synthetic_authority(payload: dict[str, Any]) -> dict[str, Any]:
    """Compile an authored arithmetic assumption, never a production document.

    Only fixture/test callers use this adapter. Missing identity is preserved;
    this cannot repair an unversioned rate. It never supplies an event date.
    Independent authority regressions call the guarded engine without this shim.
    """
    from .authority import franchise_identity_gap, franchise_terms
    from .case import Case

    result = copy.deepcopy(payload.raw if isinstance(payload, Case) else payload)
    case = Case(result)
    if case.policy.get("contract_kind") == "INSURANCE_CONTRACT":
        return result
    carrier = None
    for container in (result.get("damage", {}), result.get("vehicle", {}),
                      result.get("event", {}), result.setdefault("policy", {}), result):
        for key in ("franchise", "franchise_from_policy", "franchise_amount"):
            if isinstance(container.get(key), dict):
                carrier = container[key]
                break
        if carrier is not None:
            break
    if franchise_identity_gap(carrier) or "authority" in carrier:
        return result
    policy = result["policy"]
    policy.setdefault("insurer", "SYNTHETIC_INSURER")
    policy.setdefault("product", "SYNTHETIC_BODY")
    policy.setdefault("policy_reference", carrier["source_reference"])
    if case.event.get("event_date"):
        policy.setdefault("policy_date", case.event["event_date"])
    policy["contract_kind"] = "SYNTHETIC_TEST"
    # The content identity is of these explicit software assumptions, not a real
    # insurer artifact or a fabricated domain-review approval.
    terms = franchise_terms(carrier)
    carrier["authority"] = {
        "source_reference": carrier["source_reference"], "source_version": carrier["source_version"],
        "insurer": policy["insurer"], "product": policy["product"],
        "policy_reference": policy["policy_reference"],
        "coverage": [case.branch] if case.branch else ["PARTIAL_DAMAGE", "TOTAL_LOSS", "GLASS_ONLY", "THEFT"],
        "effective_from": "1300-01-01", "effective_until": "1500-12-29",
        "source_status": "SYNTHETIC_TEST", "governs_contract": True,
        "reviewer": "software fixture author; no qualified domain approval",
        "clause_locator": "explicit synthetic franchise assumption",
        "document_sha256": hashlib.sha256(json.dumps(terms, sort_keys=True).encode()).hexdigest(),
        "terms": terms,
    }
    return result


def load_fixtures(path: Path | str | None = None) -> list[dict[str, Any]]:
    target = Path(path) if path else FIXTURE_PATH
    payload = json.loads(target.read_text(encoding="utf-8"))
    shared_body_admission = payload.get("shared_body_admission_facts")
    fixtures = copy.deepcopy(payload["cases"])
    for fixture in fixtures:
        if _domain_for(fixture["branch"]) == "BODY":
            if not isinstance(shared_body_admission, dict):
                raise ValueError(
                    "body fixtures require explicit shared_body_admission_facts"
                )
            fixture["body_admission_facts"] = copy.deepcopy(shared_body_admission)
    return fixtures


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
    inputs = dict(fixture.get("inputs", {}))
    fixture_franchise = inputs.pop("franchise", inputs.pop("franchise_from_policy", None))
    case_payload = {
        "claim_id": fixture["id"],
        "unit": fixture.get("unit", "IRR"),
        "classification": {
            "branch": fixture["branch"],
            "domain": _domain_for(fixture["branch"]),
        },
        "damage": inputs,
    }
    for field in ("regulatory_snapshot", "vehicle", "event", "policy", "coverage_gate", "calculation_config"):
        if field in fixture:
            case_payload[field] = fixture[field]
    body_admission = fixture.get("body_admission_facts")
    if _domain_for(fixture["branch"]) == "BODY":
        if not isinstance(body_admission, dict):
            raise ValueError(
                f"body fixture {fixture['id']} has no explicit body_admission_facts"
            )
        coverage_gate = dict(body_admission.get("coverage_gate") or {})
        coverage_gate.update(case_payload.get("coverage_gate") or {})
        case_payload["coverage_gate"] = coverage_gate
        event = dict(body_admission.get("event") or {})
        event.update(case_payload.get("event") or {})
        case_payload["event"] = event
        evidence = dict(body_admission.get("evidence") or {})
        evidence.update(case_payload.get("evidence") or {})
        case_payload["evidence"] = evidence
        policy = dict(body_admission.get("policy") or {})
        policy.update(case_payload.get("policy") or {})
        case_payload["policy"] = policy
    if fixture_franchise is not None:
        policy = dict(case_payload.get("policy") or {})
        policy.setdefault("policy_version", "SYNTHETIC-FIXTURE-v1")
        policy["franchise"] = {
            "mode": "ABSOLUTE",
            "absolute_irr": fixture_franchise,
            "source": "POLICY",
            "source_reference": f"synthetic fixture {fixture['id']} franchise term",
            "source_version": "SYNTHETIC-FIXTURE-v1",
        }
        case_payload["policy"] = policy
    decision = (
        "SCENARIO_SET"
        if any(key in SCENARIO_KEYS for key in fixture.get("expected", {}))
        else "COMPUTE"
    )
    result = compute(_authorize_fixture_case(case_payload, kb, decision=decision), kb)
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
