"""Claim classifier: the top-level decision tree.

    CLAIM
    ├── establish event + vehicle + policy snapshot
    ├── coverage gate (see engine.evaluate_coverage_gate)
    ├── classify insurance/legal domain
    ├── BODY
    │   ├── whole vehicle stolen?  < 60 days -> THEFT (pending) ; >= 60 -> THEFT (total)
    │   ├── repair + rescue > 75% market value? -> TOTAL_LOSS
    │   ├── independent glass breakage? -> GLASS_ONLY
    │   └── otherwise -> PARTIAL_DAMAGE
    ├── THIRD_PARTY_FINANCIAL
    │   ├── damaged property not a passenger car? -> THIRD_PARTY_FINANCIAL
    │   ├── value < annual conventional threshold? -> THIRD_PARTY_FINANCIAL
    │   └── otherwise -> ARTICLE_8_NON_CONVENTIONAL
    └── LEGAL / RECOVERY -> LEGAL_RECOVERY

A declared branch always wins: the engine trusts an explicit classification and
only derives when the case leaves it out. Derivation confidence reports how much
of the tree was actually evaluated from evidence.
"""

from __future__ import annotations

from typing import Any

from . import money, operators
from .case import Case
from .knowledge import Knowledge

GLASS_KEYWORDS = ("GLASS", "WINDSHIELD", "BREAKAGE", "SHISHE")

THIRD_PARTY_SIGNALS = (
    "victim_vehicle_value",
    "property_type",
    "damaged_property_type",
    "tp_limit",
    "fault_status",
)


def classify(case: Case | dict[str, Any], kb: Knowledge | None = None) -> dict[str, Any]:
    from .schema_input import validated_case

    case = validated_case(case)
    kb = kb or Knowledge.load()

    basis: list[str] = []

    if case.theft_type is not None or case.days_missing is not None:
        basis.append("theft_type or days_vehicle_missing present")
        return {
            "branch": "THEFT",
            "variant": None,
            "confidence": 0.95,
            "basis": basis,
        }

    if case.domain == "LEGAL_RECOVERY":
        basis.append("classification.domain declares LEGAL_RECOVERY")
        return {"branch": "LEGAL_RECOVERY", "variant": None, "confidence": 0.9, "basis": basis}

    if case.domain == "THIRD_PARTY_FINANCIAL" or _has_third_party_signal(case):
        return _classify_third_party(case, kb, basis)

    if case.repair_total is not None and case.market_value is not None:
        is_total, combined, threshold = operators.is_total_loss(
            case.repair_total, case.rescue_for_threshold, case.market_value
        )
        basis.append(
            f"repair+rescue {combined} against 75% threshold {threshold} -> total={is_total}"
        )
        if is_total:
            return {"branch": "TOTAL_LOSS", "variant": None, "confidence": 0.97, "basis": basis}

    if case.has_glass_endorsement or _looks_like_glass(case):
        basis.append("glass endorsement or glass-only cause")
        return {"branch": "GLASS_ONLY", "variant": None, "confidence": 0.8, "basis": basis}

    basis.append("no theft, total-loss, glass or third-party signal matched")
    return {"branch": "PARTIAL_DAMAGE", "variant": None, "confidence": 0.85, "basis": basis}


def _has_third_party_signal(case: Case) -> bool:
    if case.domain == "BODY":
        return False
    return any(case.field_value(key) is not None for key in THIRD_PARTY_SIGNALS)


def _classify_third_party(case: Case, kb: Knowledge, basis: list[str]) -> dict[str, Any]:
    basis.append("third-party financial domain")
    if case.property_type != "PASSENGER_VEHICLE":
        basis.append(f"damaged property is {case.property_type}, not a passenger car")
        return {
            "branch": "THIRD_PARTY_FINANCIAL",
            "variant": "ORDINARY_FINANCIAL",
            "confidence": 0.95,
            "basis": basis,
        }

    value = case.victim_vehicle_value
    threshold = case.threshold
    if threshold is None:
        irr = kb.annual_value(case.claim_year, "CONVENTIONAL_THRESHOLD")
        threshold = None if irr is None else money.D(irr)
    if value is None or threshold is None:
        basis.append("vehicle value or annual threshold unavailable; defaulting to the ordinary cap")
        return {
            "branch": "THIRD_PARTY_FINANCIAL",
            "variant": "ORDINARY_FINANCIAL",
            "confidence": 0.5,
            "basis": basis,
        }

    if value < threshold:
        basis.append(f"value {value} < conventional threshold {threshold}")
        return {
            "branch": "THIRD_PARTY_FINANCIAL",
            "variant": "ORDINARY_FINANCIAL",
            "confidence": 0.97,
            "basis": basis,
        }

    basis.append(f"value {value} >= conventional threshold {threshold}")
    return {
        "branch": "ARTICLE_8_NON_CONVENTIONAL",
        "variant": None,
        "confidence": 0.97,
        "basis": basis,
    }


def _looks_like_glass(case: Case) -> bool:
    haystack = " ".join(filter(None, [case.cause or "", case.peril or ""])).upper()
    return any(keyword in haystack for keyword in GLASS_KEYWORDS)
