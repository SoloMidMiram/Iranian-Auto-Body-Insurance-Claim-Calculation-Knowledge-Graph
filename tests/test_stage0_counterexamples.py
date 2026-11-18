"""Strict counterexamples pinned by PR-00 without changing settlement semantics.

Every expected failure names the audit finding that owns it.  A remediation PR
must first demonstrate that its case failed on the parent revision, then remove
the marker when the new invariant passes.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from iran_auto_claim.admission import _internal_test_direct_authorize
from iran_auto_claim.engine import compute
from iran_auto_claim.review import Review
from iran_auto_claim.schema_input import InputSchemaError


REPOSITORY = Path(__file__).resolve().parents[1]
CASES = REPOSITORY / "cases"


def _review_case(name: str = "review_t1_fullcover_partial.json") -> dict:
    return json.loads((CASES / name).read_text(encoding="utf-8"))


def _assert_review_does_not_pay(payload: dict, kb) -> None:
    try:
        result = Review(payload, kb).calculate()
    except InputSchemaError:
        return
    assert result is None or result.payable is None


def _total_loss_direct_case() -> dict:
    return {
        "claim_id": "stage0-ia14-total",
        "unit": "IRR",
        "classification": {"branch": "TOTAL_LOSS"},
        "event": {"event_date": "1405-01-01"},
        "coverage_gate": {"causal_relationship_established": True},
        "vehicle": {
            "market_value_at_event_irr": 2000,
            "insured_sum_irr": 2000,
        },
        "damage": {
            "repair_total_irr": 1600,
            "rescue_for_total_loss_test_irr": 0,
        },
        "policy": {
            "policy_version": "STAGE0-v1",
            "multiple_insurance": {"state": "NO", "prior_compensation": 0},
            "franchise": {
                "mode": "ABSOLUTE",
                "absolute_irr": 100,
                "source": "POLICY",
                "source_reference": "Stage 0 control schedule",
                "source_version": "STAGE0-v1",
            },
        },
    }


def test_stage0_control_supported_review_path_remains_collectable(kb):
    result = Review(_review_case(), kb).calculate()
    assert result is not None
    assert result.branch == "PARTIAL_DAMAGE"
    assert result.payable == 1657000000


def test_stage0_control_complete_internal_total_loss_remains_collectable(kb):
    payload = _total_loss_direct_case()
    payload["vehicle"].update(
        {
            "salvage_value_irr": 300,
            "salvage_disposition": "INSURED_RETAINS",
        }
    )
    result = compute(
        _internal_test_direct_authorize(payload, purpose="STAGE0_SUPPORTED_CONTROL"),
        kb,
    )
    assert result.payable == 1600
    assert result.fields["salvage_deduction"] == 300


def test_ia01_prior_compensation_blocks_a_single_payable(kb):
    payload = _review_case()
    payload["answers"]["Q-S9-03"] = 1850000000
    payload["answers"]["Q-S6-05"] = "YES_OTHER_POLICIES"
    payload["evidence_present"] += [
        "EVT_OTHER_POLICIES",
        "EVT_ARBITRATION_OR_COURT_AWARD",
    ]
    _assert_review_does_not_pay(payload, kb)


def test_ia02_asserted_only_causation_blocks_a_single_payable(kb):
    payload = _review_case()
    payload["answers"]["Q-S2-02"] = "ASSERTED_ONLY"
    _assert_review_does_not_pay(payload, kb)


def test_ia03_repair_only_component_has_no_replacement_depreciation(kb):
    payload = _review_case()
    payload["answers"]["Q-S4-03"] = [
        {
            "category": "REPAIR_ONLY",
            "assessed_loss": 1200000000,
            "requires_replacement": False,
        }
    ]
    result = Review(payload, kb).calculate()
    assert result is not None
    assert result.fields["depreciation"] == 0
    assert result.payable == 1540000000


def test_ia04_rescue_crossing_the_strict_threshold_classifies_total_loss(kb):
    payload = _review_case()
    payload["answers"]["Q-S5-01"] = 10000
    payload["answers"]["Q-S5-02"] = 10000
    payload["answers"]["Q-S5-03"] = 1404
    payload["answers"]["Q-S4-02"] = 0
    payload["answers"]["Q-S4-03"] = [
        {"category": "OTHER_REPLACEMENT_PART", "assessed_loss": 7400}
    ]
    payload["answers"]["Q-S4-07"] = 200
    assert Review(payload, kb).classification()["branch"] == "TOTAL_LOSS"


@pytest.mark.xfail(strict=True, reason="IA-05: insurer-title settlement requires completed transfer")
def test_ia05_incomplete_title_transfer_cannot_pay_total_loss(kb):
    payload = _review_case()
    payload["answers"]["Q-S4-03"][0]["assessed_loss"] = 6500000000
    payload["answers"]["Q-S4-08"] = 1000000000
    payload["answers"]["Q-S4-09"] = "INSURER_TAKES_TITLE"
    payload["answers"]["Q-S4-06"] = "NOT_TRANSFERRED"
    payload["evidence_present"] += [
        "EVT_SALVAGE_VALUATION",
        "EVT_TITLE_TRANSFER_PROOF",
    ]
    for question in ("Q-S6-02", "Q-S6-03"):
        payload["answers"][question]["calculation_base"] = "SETTLEMENT_BASE"
    _assert_review_does_not_pay(payload, kb)


@pytest.mark.parametrize(
    ("question", "value"),
    [("Q-S0-02", "1404-99-99"), ("Q-S5-03", 1500)],
    ids=("invalid-event-date", "production-after-event"),
)
def test_ia07_invalid_chronology_cannot_pay(kb, question, value):
    payload = _review_case()
    payload["answers"][question] = value
    _assert_review_does_not_pay(payload, kb)


@pytest.mark.xfail(strict=True, reason="IA-08: an unversioned manual cannot establish a monetary franchise")
def test_ia08_unversioned_manual_franchise_cannot_pay(kb):
    payload = _review_case()
    for question in ("Q-S6-02", "Q-S6-04"):
        payload["answers"][question]["source"] = "INSURER_MANUAL"
        payload["answers"][question].pop("source_reference", None)
        payload["answers"][question].pop("source_version", None)
    _assert_review_does_not_pay(payload, kb)


def test_ia15_conflicting_part_aliases_are_rejected(kb):
    payload = _review_case()
    payload["answers"]["Q-S4-03"][0]["assessed_loss_irr"] = 1
    with pytest.raises(InputSchemaError):
        Review(payload, kb)


@pytest.mark.xfail(strict=True, reason="IA-14: material salvage operands are mandatory at the engine boundary")
@pytest.mark.parametrize(
    "disposition",
    [None, "INSURED_RETAINS"],
    ids=("disposition-absent", "retained-value-absent"),
)
def test_ia14_internal_total_loss_missing_salvage_cannot_pay(kb, disposition):
    payload = _total_loss_direct_case()
    if disposition is not None:
        payload["vehicle"]["salvage_disposition"] = disposition
    result = compute(
        _internal_test_direct_authorize(payload, purpose="STAGE0_IA14_COUNTEREXAMPLE"),
        kb,
    )
    assert result.payable is None
