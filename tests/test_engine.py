"""Engine-level behaviour: classification, dispatch, confidence, refusals."""

from __future__ import annotations

from decimal import Decimal

import pytest

from iran_auto_claim.classify import classify
from iran_auto_claim.engine import compute
from iran_auto_claim.money import D
from iran_auto_claim.schema_input import InputSchemaError


def _case(branch=None, **inputs):
    payload = {"claim_id": "engine-test", "unit": "million_toman", "damage": inputs}
    if branch:
        payload["classification"] = {"branch": branch}
    return payload


# --------------------------------------------------------------- classifier


def test_classifier_routes_total_loss():
    verdict = classify(_case("TOTAL_LOSS", market=2000, repair=1600))
    assert verdict["branch"] == "TOTAL_LOSS"


def test_classifier_keeps_a_partial_loss_partial():
    verdict = classify(_case("PARTIAL_DAMAGE", market=2000, repair=1500))
    assert verdict["branch"] == "PARTIAL_DAMAGE"


def test_classifier_routes_theft_and_glass():
    assert classify(_case("THEFT", theft_type="WHOLE_VEHICLE", days_missing=10))["branch"] == "THEFT"
    assert classify(_case("GLASS_ONLY", glass_endorsement=True, gross=50))["branch"] == "GLASS_ONLY"


def test_classifier_splits_conventional_and_non_conventional():
    conventional = classify(
        _case("THIRD_PARTY_FINANCIAL", victim_vehicle_value=1000, conventional_threshold=1400)
    )
    assert conventional["branch"] == "THIRD_PARTY_FINANCIAL"

    non_conventional = classify(
        _case("THIRD_PARTY_FINANCIAL", victim_vehicle_value=1400, conventional_threshold=1400)
    )
    assert non_conventional["branch"] == "ARTICLE_8_NON_CONVENTIONAL"


def test_a_declared_branch_wins_over_derivation(kb):
    payload = _case("PARTIAL_DAMAGE", gross=1600)
    result = compute(payload, kb)
    assert result.branch == "PARTIAL_DAMAGE"
    assert "PARTIAL_DAMAGE" in result.labels
    assert result.payable == D(1600)
    assert "classification" not in result.fields, "a declared branch must not be re-derived"


def test_a_partial_claim_with_no_assessed_damage_is_an_input_error(kb):
    result = compute(_case("PARTIAL_DAMAGE", market=2000, repair_total=1600), kb)
    assert result.status == "INPUT_ERROR"


def test_an_unknown_part_category_is_refused_rather_than_silently_depreciated(kb):
    payload = _case(
        "PARTIAL_DAMAGE",
        parts=[{"category": "BATTERY_TYPO", "assessed_loss": 100}],
    )
    with pytest.raises(InputSchemaError) as caught:
        compute(payload, kb)
    assert any(
        item.code == "invalid_enum" and item.path == "damage.parts[0].category"
        for item in caught.value.errors
    )


def test_engine_derives_when_no_branch_is_declared(kb):
    result = compute(_case(market=2000, insured=2000, repair=1600, franchise=100), kb)
    assert result.branch == "TOTAL_LOSS"
    assert result.fields["classification"]["branch"] == "TOTAL_LOSS"
    assert result.fields["classification"]["basis"]


# ----------------------------------------------------------------- dispatch


def test_unknown_branch_is_rejected_by_the_schema(kb):
    with pytest.raises(InputSchemaError) as caught:
        compute(_case("NOT_A_BRANCH"), kb)
    assert any(item.code == "invalid_enum" and item.path == "classification.branch" for item in caught.value.errors)


def test_missing_insured_sum_alongside_a_market_value_is_an_input_error(kb):
    result = compute(_case("PARTIAL_DAMAGE", market=3000, gross=100, franchise=10), kb)
    assert result.status == "INPUT_ERROR"
    assert "insured sum" in result.reason


def test_missing_market_value_alongside_an_insured_sum_is_an_input_error(kb):
    result = compute(_case("PARTIAL_DAMAGE", insured=3000, gross=100, franchise=10), kb)
    assert result.status == "INPUT_ERROR"


def test_total_loss_settlement_requires_both_figures(kb):
    payload = _case("TOTAL_LOSS", market=2000, salvage_value=300, franchise=100)
    result = compute(payload, kb)
    assert result.status == "INPUT_ERROR"


def test_title_transfer_is_required_before_a_theft_total_settlement(kb):
    result = compute(
        _case(
            "THEFT",
            theft_type="WHOLE_VEHICLE",
            days_missing=65,
            market=2200,
            insured=2200,
            franchise=220,
            title_transferred=False,
        ),
        kb,
    )
    assert result.payable is None
    assert result.status == "TITLE_TRANSFER_REQUIRED"


# --------------------------------------------------------------- confidence


def test_confidence_model_is_computed_from_the_trace(kb):
    # P01-class claim: every cited rule is explicit regulatory text
    confident = compute(
        _case("PARTIAL_DAMAGE", market=3000, insured=3000, gross=100, depreciation=0, franchise=10),
        kb,
    )
    assert confident.formula_confidence is not None
    assert confident.formula_confidence >= 0.95

    # P10-class claim: the operator order is unresolved, so the single-
    # interpretation confidence of that uncertainty caps the result
    unresolved = compute(
        _case("PARTIAL_DAMAGE", market=4000, insured=3000, gross=400, depreciation=20, franchise=40),
        kb,
    )
    assert unresolved.formula_confidence == 0.55


def test_an_unknown_branch_never_receives_a_confidence_figure(kb):
    with pytest.raises(InputSchemaError):
        compute(_case("NOT_A_BRANCH"), kb)


# ---------------------------------------------------------------- provenance


def test_provenance_is_attached_for_every_cited_rule(kb):
    result = compute(
        _case("PARTIAL_DAMAGE", market=3000, insured=3000, gross=100, franchise=10), kb
    )
    assert result.rule_trace
    cited = {entry["node_id"] for entry in result.provenance}
    assert cited == set(result.rule_trace)
    for entry in result.provenance:
        assert entry["source_class"] in ("STATUTE", "REGULATION", "CIRCULAR")
        assert entry["confidence"] is not None
        assert entry["sources"]


def test_depreciation_is_zero_for_glass_inside_a_mixed_claim(kb):
    result = compute(
        _case(
            "PARTIAL_DAMAGE",
            gross=80,
            replacement_parts=[{"type": "GLASS", "loss": 80}],
            franchise=16,
        ),
        kb,
    )
    assert result.fields["glass_depreciation"] == D(0)
    assert result.fields["depreciation"] == D(0)


def test_rescue_cap_base_is_recorded_and_configurable(kb):
    payload = _case("PARTIAL_DAMAGE", gross=200, franchise=20, actual_rescue=60)
    payload["calculation_config"] = {"rescue_cap_base": "ELIGIBLE_GROSS"}
    result = compute(payload, kb)
    assert result.fields["rescue_cap_base_kind"] == "ELIGIBLE_GROSS"
    assert result.fields["rescue_cap"] == D(40)


def test_dual_coverage_reports_the_body_candidate_without_a_mandatory_franchise(kb):
    result = compute(
        _case(
            "ARTICLE_8_DUAL_COVERAGE",
            vehicle_value=2500,
            actual_damage=300,
            corresponding_damage=180,
            tp_limit=200,
            has_body_policy=True,
            body_franchise_for_excess_disclosed=False,
        ),
        kb,
    )
    assert result.fields["third_party"] == D(180)
    assert result.fields["body_candidate_before_other_body_terms"] == D(120)
    assert result.fields["regulatory_mandatory_franchise_on_this_excess"] == D(0)


def test_interest_of_the_insured_is_reported_for_a_single_payable_result(kb):
    result = compute(_case("PARTIAL_DAMAGE", gross=100, franchise=10), kb)
    assert result.payable_is_single
    assert result.payable == D(90)
    assert result.fields["franchise"] == D(10)
