"""Authority identity regressions; applicability is a separate required layer."""
import copy
import json
from pathlib import Path

import pytest

from iran_auto_claim.admission import _internal_test_direct_authorize
from iran_auto_claim.engine import compute
from iran_auto_claim.review import Review


ROOT = Path(__file__).resolve().parents[1]

RATIO_FIRST = "AFTER_DEPRECIATION_BEFORE_FRANCHISE"
FRANCHISE_FIRST = "AFTER_DEPRECIATION_AND_FRANCHISE"


def controlled_partial(order="UNRESOLVED"):
    from iran_auto_claim.fixtures import _with_synthetic_authority
    return _with_synthetic_authority({
        "claim_id": "S10-INDEPENDENT-1000-100-08", "unit": "IRR",
        "classification": {"branch": "PARTIAL_DAMAGE"},
        "event": {"event_date": "1404-08-20"},
        "vehicle": {"market_value_at_event_irr": 10000, "insured_sum_irr": 8000},
        "damage": {"gross_damage_irr": 1000, "assessed_depreciation_irr": 0,
                   "repair_total_irr": 1000, "rescue_for_total_loss_test_irr": 0,
                   "rescue_transport_actual_irr": 0},
        "coverage_gate": {"causal_relationship_established": True},
        "policy": {"insurer": "SYNTHETIC_INSURER", "product": "SYNTHETIC_BODY",
                   "policy_reference": "CONTROL-POLICY", "policy_date": "1404-01-01",
                   "contract_kind": "SYNTHETIC_TEST",
                   "multiple_insurance": {"state": "NO", "prior_compensation": 0},
                   "franchise": {"mode": "ABSOLUTE", "absolute_irr": 100,
                                 "source": "POLICY", "source_reference": "synthetic clause",
                                 "source_version": "TEST-v1"}},
        "calculation_config": {"article10_partial_order": order},
    })


def synthetic_order_authority(order):
    import hashlib
    return {
        "source_reference": "SYNTHETIC ordering instrument", "source_version": "TEST-v1",
        "insurer": "SYNTHETIC_INSURER", "product": "SYNTHETIC_BODY",
        "policy_reference": "CONTROL-POLICY", "effective_from": "1404-01-01",
        "effective_until": "1404-12-29", "coverage": ["PARTIAL_DAMAGE"],
        "source_status": "SYNTHETIC_TEST", "governs_contract": True,
        "reviewer": "synthetic test author; no human domain approval",
        "clause_locator": "software oracle order assumption",
        "document_sha256": hashlib.sha256(b"synthetic order assumption").hexdigest(),
        "terms": {"article10_partial_order": order},
    }


def direct_result(payload, kb):
    return compute(_internal_test_direct_authorize(payload, purpose="S05_S10_AUTHORITY_REGRESSION"), kb)


@pytest.mark.parametrize("order", ["UNRESOLVED", RATIO_FIRST, FRANCHISE_FIRST])
def test_unproved_order_retains_both_independent_scenarios(kb, order):
    result = direct_result(controlled_partial(order), kb)
    assert result.payable is None
    assert result.payable_scenarios == [700, 720]
    assert result.status == "ORDER_UNRESOLVED"
    assert "U01_ARTICLE10_PARTIAL_ORDER" in result.blocking_uncertainties


@pytest.mark.parametrize("order,amount", [(RATIO_FIRST, 700), (FRANCHISE_FIRST, 720)])
def test_complete_synthetic_order_record_selects_only_its_bound_order(kb, order, amount):
    payload = controlled_partial(order)
    payload["calculation_config"]["article10_order_authority"] = synthetic_order_authority(order)
    assert direct_result(payload, kb).payable == amount


@pytest.mark.parametrize("field,value", [
    ("insurer", "WRONG"), ("product", "WRONG"), ("coverage", ["THEFT"]),
    ("source_status", "UNRESOLVED"), ("source_version", ""),
    ("effective_until", "1403-12-29"), ("effective_from", "1405-01-01"),
    ("governs_contract", False), ("terms", {"article10_partial_order": FRANCHISE_FIRST}),
])
def test_inapplicable_or_conflicting_order_record_keeps_scenarios(kb, field, value):
    payload = controlled_partial(RATIO_FIRST)
    record = synthetic_order_authority(RATIO_FIRST)
    record[field] = value
    payload["calculation_config"]["article10_order_authority"] = record
    if field == "source_version":
        record.pop(field)  # Absence must be nonpayable, not silently supplied.
    result = direct_result(payload, kb)
    assert result.payable is None
    assert result.payable_scenarios == [700, 720]


def test_review_token_keeps_scenarios_instead_of_losing_them(kb):
    payload = json.loads((ROOT / "cases/review_t1_fullcover_partial.json").read_text())
    answers = payload["answers"]
    answers.update({"Q-S4-02": 0, "Q-S4-03": [{"category": "REPAIR_ONLY", "assessed_loss": 1000,
                                               "requires_replacement": False}],
                    "Q-S4-07": 0, "Q-S5-01": 10000, "Q-S5-02": 8000,
                    "Q-S5-04": "UNDERINSURANCE_CLEAR", "Q-S6-01": "ABSOLUTE", "Q-S8-01": RATIO_FIRST})
    for question in ("Q-S6-02", "Q-S6-03", "Q-S6-04"):
        answers[question] = controlled_partial()["policy"]["franchise"]
    payload["contract_context"] = {k: controlled_partial()["policy"][k] for k in
                                   ("insurer", "product", "policy_reference", "policy_date", "contract_kind")}
    review = Review(payload, kb)
    result = review.calculate()
    assert result is not None and result.payable is None
    assert result.payable_scenarios == [700, 720]
    assert result.status == "ORDER_UNRESOLVED"


@pytest.mark.parametrize("source", ["POLICY", "ENDORSEMENT", "INSURER_MANUAL"])
@pytest.mark.parametrize("amount", [0, 100])
@pytest.mark.parametrize("field,value", [("source_reference", None), ("source_version", None), ("source_reference", " "), ("source_version", " ")])
def test_review_and_engine_refuse_unidentifiable_franchise(kb, source, amount, field, value):
    payload = json.loads((ROOT / "cases/review_t1_fullcover_partial.json").read_text(encoding="utf-8"))
    payload["answers"]["Q-S6-01"] = "ABSOLUTE"
    for question in ("Q-S6-02", "Q-S6-03", "Q-S6-04"):
        spec = {"mode": "ABSOLUTE", "absolute_irr": amount, "source": source,
                "source_reference": "SYNTHETIC contract clause", "source_version": "TEST-v1"}
        if value is None:
            spec.pop(field)
        else:
            spec[field] = value
        payload["answers"][question] = spec
    review = Review(payload, kb)
    assert review.decision()["decision"] == "INSUFFICIENT_INFORMATION"
    assert "U02_FRANCHISE_BASE_SCHEDULES" in review.open_uncertainties()
    assert review.calculate() is None
    raw = copy.deepcopy(review.case_payload())
    result = compute(_internal_test_direct_authorize(raw, purpose="S09_IDENTITY_COUNTEREXAMPLE"), kb)
    assert result.payable is None
    assert result.status == "FRANCHISE_AUTHORITY_REQUIRED"
    assert "U02_FRANCHISE_BASE_SCHEDULES" in result.blocking_uncertainties


@pytest.mark.parametrize("field,value", [
    ("insurer", "WRONG"), ("product", "WRONG"), ("coverage", ["THEFT"]),
    ("effective_until", "1403-12-29"), ("effective_from", "1405-01-01"),
    ("source_status", "UNRESOLVED"), ("governs_contract", False),
    ("source_version", "DIFFERENT-VERSION"),
])
def test_franchise_applicability_is_required_at_both_boundaries(kb, field, value):
    from contract_assumptions import with_review_contract
    payload = json.loads((ROOT / "cases/review_t1_fullcover_partial.json").read_text())
    payload = with_review_contract(payload, kb)
    payload["answers"]["Q-S6-04"]["authority"][field] = value
    review = Review(payload, kb)
    assert review.decision()["decision"] == "INSUFFICIENT_INFORMATION"
    assert review.calculate() is None
    result = direct_result(review.case_payload(), kb)
    assert result.payable is None
    assert result.status == "FRANCHISE_AUTHORITY_REQUIRED"


@pytest.mark.parametrize("amount", [0, 100])
def test_complete_absolute_franchise_preserves_zero_and_positive_controls(kb, amount):
    from iran_auto_claim.fixtures import _with_synthetic_authority
    payload = controlled_partial()
    payload["vehicle"]["insured_sum_irr"] = 10000
    payload["policy"]["franchise"]["absolute_irr"] = amount
    payload["policy"]["franchise"].pop("authority")
    result = direct_result(_with_synthetic_authority(payload), kb)
    assert result.payable == 1000 - amount


def test_percentage_franchise_keeps_its_bound_base_and_unresolved_order(kb):
    from iran_auto_claim.fixtures import _with_synthetic_authority
    payload = controlled_partial()
    payload["policy"]["franchise"] = {
        "mode": "PERCENT", "rate": 0.1, "calculation_base": "AFTER_DEPRECIATION",
        "source": "POLICY", "source_reference": "SYNTHETIC percentage contract", "source_version": "TEST-v1"}
    result = direct_result(_with_synthetic_authority(payload), kb)
    assert result.payable is None
    assert result.payable_scenarios == [700, 720]
    assert result.fields["franchise_calculation_base"] == 1000


def test_conflicting_policy_and_endorsement_declarations_do_not_get_merged(kb):
    payload = json.loads((ROOT / "cases/review_t1_fullcover_partial.json").read_text())
    payload["answers"]["Q-S6-02"]["source"] = "ENDORSEMENT"
    payload["answers"]["Q-S6-02"]["rate"] = 0.2
    decision = Review(payload, kb).decision()
    assert decision["decision"] == "INSUFFICIENT_INFORMATION"
    assert "FRANCHISE_TERMS_CONFLICT" in decision["blocking_conditions"]


def test_conflicting_salvage_evidence_and_values_are_rejected(kb):
    from iran_auto_claim.schema_input import InputSchemaError
    from test_stage0_counterexamples import _total_loss_direct_case
    for field, value in (("salvage_disposition", "INSURER_TAKES_TITLE"), ("salvage", 99)):
        payload = _total_loss_direct_case()
        payload["vehicle"].update(salvage_disposition="INSURED_RETAINS", salvage_value_irr=300)
        payload["damage"][field] = value
        with pytest.raises(InputSchemaError):
            direct_result(payload, kb)


@pytest.mark.parametrize("route", ["INSURED_RETAINS", "INSURER_TAKES_TITLE"])
def test_engine_demands_supporting_settlement_evidence_even_for_explicit_values(kb, route):
    from test_stage0_counterexamples import _total_loss_direct_case
    payload = _total_loss_direct_case()
    payload["vehicle"].update(salvage_disposition=route, salvage_value_irr=0, title_transferred=True)
    payload["evidence"] = {}
    result = direct_result(payload, kb)
    assert result.payable is None
    assert result.status in ("TITLE_TRANSFER_REQUIRED", "SALVAGE_VALUATION_EVIDENCE_REQUIRED")


def test_equal_order_outcomes_do_not_invent_ordering_authority(kb):
    from iran_auto_claim.fixtures import _with_synthetic_authority
    payload = controlled_partial(RATIO_FIRST)
    payload["policy"]["franchise"]["absolute_irr"] = 0
    payload["policy"]["franchise"].pop("authority")
    result = direct_result(_with_synthetic_authority(payload), kb)
    assert result.payable is None
    assert result.payable_scenarios == [800, 800]
    assert "U01_ARTICLE10_PARTIAL_ORDER" in result.blocking_uncertainties


def test_ratio_one_preserves_arithmetic_without_asserting_universal_order(kb):
    payload = controlled_partial(RATIO_FIRST)
    payload["vehicle"]["insured_sum_irr"] = 10000
    result = direct_result(payload, kb)
    assert result.payable == 900
    assert result.fields["order_used"] == "RATIO_NOT_APPLICABLE"
