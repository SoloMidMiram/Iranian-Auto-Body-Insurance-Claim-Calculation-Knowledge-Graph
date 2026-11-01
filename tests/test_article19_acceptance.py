"""Independent boundary assertions; amounts are synthetic software oracles."""
import json
from pathlib import Path

import pytest

from iran_auto_claim.admission import _internal_test_direct_authorize
from iran_auto_claim.case import Case
from iran_auto_claim.classify import classify
from iran_auto_claim.engine import compute
from iran_auto_claim.review import Review
from test_stage0_counterexamples import _total_loss_direct_case


def direct(payload, kb):
    return compute(_internal_test_direct_authorize(payload, purpose="ARTICLE19_ACCEPTANCE"), kb)


@pytest.mark.parametrize("repair,rescue,expected", [(7500, 0, "PARTIAL_DAMAGE"), (7400, 200, "TOTAL_LOSS")])
def test_classification_independent_of_settlement(kb, repair, rescue, expected):
    payload = _total_loss_direct_case()
    payload["vehicle"]["market_value_at_event_irr"] = 10000
    payload["damage"].update(repair_total_irr=repair, rescue_for_total_loss_test_irr=rescue)
    payload.pop("policy")
    assert classify(Case(payload), kb)["branch"] == expected


@pytest.mark.parametrize("disposition", [None, "UNRESOLVED", "NOT_APPLICABLE", "INSURED_RETAINS"])
def test_missing_salvage_never_becomes_zero(kb, disposition):
    payload = _total_loss_direct_case()
    if disposition is not None:
        payload["vehicle"]["salvage_disposition"] = disposition
    result = direct(payload, kb)
    assert result.payable is None
    assert result.payable_scenarios == []
    assert result.status in ("SALVAGE_DISPOSITION_UNRESOLVED", "SALVAGE_VALUE_REQUIRED")


def test_explicit_zero_salvage_is_a_real_operand(kb):
    payload = _total_loss_direct_case()
    payload["vehicle"].update(salvage_disposition="INSURED_RETAINS", salvage_value_irr=0)
    result = direct(payload, kb)
    assert result.payable == 1900
    assert result.fields["salvage_deduction"] == 0


@pytest.mark.parametrize("transferred", [None, False, True])
def test_direct_title_route(kb, transferred):
    payload = _total_loss_direct_case()
    payload["vehicle"].update(salvage_disposition="INSURER_TAKES_TITLE", salvage_value_irr=300)
    if transferred is not None:
        payload["vehicle"]["title_transferred"] = transferred
    result = direct(payload, kb)
    if transferred is True:
        assert result.payable == 1900
        assert result.fields["salvage_deduction"] == 0
    else:
        assert result.payable is None
        assert result.status == "TITLE_TRANSFER_REQUIRED"


@pytest.mark.parametrize("disposition,value", [(None, None), ("UNRESOLVED", None), ("NOT_APPLICABLE", None), ("INSURED_RETAINS", None), ("INSURED_RETAINS", 0)])
def test_review_salvage_requires_supported_route_and_value(kb, disposition, value):
    payload = json.loads((Path(__file__).parents[1] / "cases/inspection-c63-retains-after-salvage.json").read_text())
    answers = payload["answers"]
    answers.pop("Q-S4-09", None)
    answers.pop("Q-S4-08", None)
    if disposition is not None:
        answers["Q-S4-09"] = disposition
    if value is not None:
        answers["Q-S4-08"] = value
    # A numerical assertion without its valuation artifact must not authorize.
    payload["evidence_present"] = [x for x in payload["evidence_present"] if x != "EVT_SALVAGE_VALUATION"]
    review = Review(payload, kb)
    assert review.decision()["decision"] not in ("COMPUTE", "SCENARIO_SET")
    assert review.calculate() is None


def test_review_completed_title_without_proof_cannot_authorize(kb):
    payload = json.loads((Path(__file__).parents[1] / "cases/inspection-c62-title-transferred.json").read_text())
    payload["evidence_present"] = [x for x in payload["evidence_present"] if x != "EVT_TITLE_TRANSFER_PROOF"]
    review = Review(payload, kb)
    assert review.decision()["decision"] == "INSUFFICIENT_INFORMATION"
    assert review.calculate() is None


def test_review_evidenced_zero_salvage_preserves_supported_route(kb):
    payload = json.loads((Path(__file__).parents[1] / "cases/inspection-c63-retains-after-salvage.json").read_text())
    payload["answers"]["Q-S4-08"] = 0
    assert "EVT_SALVAGE_VALUATION" in payload["evidence_present"]
    result = Review(payload, kb).calculate()
    assert result is not None and result.payable is not None
    assert result.fields["salvage_deduction"] == 0
