"""Engine-level behaviour: classification, dispatch, confidence, refusals."""

from __future__ import annotations

from decimal import Decimal

import pytest
from admission_shim import compute

from iran_auto_claim.classify import classify
from iran_auto_claim.money import D
from iran_auto_claim.schema_input import InputSchemaError


def _case(branch=None, **inputs):
    franchise = inputs.pop("franchise", None)
    payload = {"claim_id": "engine-test", "unit": "IRR", "damage": inputs}
    if franchise is not None:
        payload["policy"] = {
            "policy_version": "TEST-v1",
            "franchise": {
                "mode": "ABSOLUTE",
                "absolute_irr": franchise,
                "source": "POLICY",
                "source_reference": "test policy schedule",
                "source_version": "TEST-v1",
            },
        }
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


def test_free_text_that_mentions_a_peril_does_not_exclude_cover(kb):
    narrative = _case(
        "PARTIAL_DAMAGE",
        gross=1600,
        franchise=100,
        cause="the road flooded after rain but this is not a flood peril code",
    )
    result = compute(narrative, kb)
    assert result.payable == D(1500)
    coded = _case("PARTIAL_DAMAGE", gross=1600, franchise=100, peril="FLOOD")
    excluded = compute(coded, kb)
    assert excluded.payable == D(0)
    assert excluded.reason == "EXCLUDED_WITHOUT_ENDORSEMENT"


def test_a_body_claim_without_a_resolvable_snapshot_does_not_run_operators(kb):
    payload = _case("PARTIAL_DAMAGE", gross=1600, franchise=100)
    payload["event"] = {"event_date": "1200/01/01"}
    result = compute(payload, kb)
    assert result.status == "INSUFFICIENT_INFORMATION"
    assert result.payable is None
    assert result.rule_trace == []


def test_a_dated_body_claim_records_its_snapshot(kb):
    payload = _case("PARTIAL_DAMAGE", gross=1600, franchise=100)
    payload["event"] = {"event_date": "1405/06/01"}
    payload["regulatory_snapshot"] = {"iranian_year": 1405}
    result = compute(payload, kb)
    assert result.payable == D(1500)
    assert result.fields["snapshot_id"] == "BODY@1405/06/01"


def test_a_declared_branch_matching_evidence_is_reconciled(kb):
    payload = _case("PARTIAL_DAMAGE", gross=1600, franchise=100)
    result = compute(payload, kb)
    assert result.branch == "PARTIAL_DAMAGE"
    assert "PARTIAL_DAMAGE" in result.labels
    assert result.payable == D(1500)
    assert result.fields["classification"]["outcome"] == "MATCH"
    assert result.fields["classification"]["declared_branch"] == "PARTIAL_DAMAGE"
    assert result.fields["classification"]["derived_branch"] == "PARTIAL_DAMAGE"


def test_a_declared_partial_branch_conflicting_with_total_evidence_is_blocked(kb):
    result = compute(_case("PARTIAL_DAMAGE", market=2000, repair_total=1600), kb)
    assert result.status == "CLASSIFICATION_CONFLICT"
    assert result.payable is None


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
    assert result.fields["classification"]["derived_branch"] == "TOTAL_LOSS"
    assert result.fields["classification"]["outcome"] == "MATCH"
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
    payload = _case("TOTAL_LOSS", market=2000, repair=1600, salvage_value=300, franchise=100)
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
    payload = _case(
            "PARTIAL_DAMAGE",
            gross=80,
            production_year=1405,
            replacement_parts=[{"type": "GLASS", "loss": 80}],
            franchise=16,
    )
    payload["regulatory_snapshot"] = {"iranian_year": 1405}
    result = compute(payload, kb)
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


@pytest.mark.parametrize(
    "payload",
    [
        _case("PARTIAL_DAMAGE", gross=100),
        _case("TOTAL_LOSS", market=2000, insured=2000, repair=1600, salvage=100),
        _case("GLASS_ONLY", glass_endorsement=True, gross=100),
        _case(
            "THEFT",
            theft_type="WHOLE_VEHICLE",
            days_missing=65,
            market=2000,
            insured=2000,
            title_transferred=True,
        ),
    ],
)
def test_body_settlement_without_franchise_terms_blocks_on_u02(kb, payload):
    result = compute(payload, kb)
    assert result.payable is None
    assert result.payable_scenarios == []
    assert result.status == "FRANCHISE_TERMS_REQUIRED"
    assert result.blocking_uncertainties == ["U02_FRANCHISE_BASE_SCHEDULES"]
    assert "policy/product/version" in result.fields["franchise_evidence_needed"]


def test_scalar_zero_franchise_does_not_mean_no_franchise_coverage(kb):
    payload = _case("PARTIAL_DAMAGE", gross=100)
    payload["damage"]["franchise"] = 0
    result = compute(payload, kb)
    assert result.payable is None
    assert result.status == "FRANCHISE_AUTHORITY_REQUIRED"
    assert result.blocking_uncertainties == ["U02_FRANCHISE_BASE_SCHEDULES"]


def test_unsourced_absolute_franchise_is_not_authority(kb):
    payload = _case("PARTIAL_DAMAGE", gross=100)
    payload["policy"] = {
        "franchise": {
            "mode": "ABSOLUTE",
            "absolute_irr": 10,
            "source": "UNKNOWN",
        }
    }
    result = compute(payload, kb)
    assert result.payable is None
    assert result.status == "FRANCHISE_AUTHORITY_REQUIRED"
    assert result.blocking_uncertainties == ["U02_FRANCHISE_BASE_SCHEDULES"]
    assert "policy/product/version" in result.fields["franchise_evidence_needed"]


def test_versioned_policy_evidence_can_explicitly_set_zero_franchise(kb):
    payload = _case("PARTIAL_DAMAGE", gross=100)
    payload["policy"] = {
        "policy_version": "BODY-1405-v1",
        "franchise": {
            "mode": "ABSOLUTE",
            "absolute_irr": 0,
            "source": "POLICY",
            "source_reference": "declarations page, franchise line",
            "source_version": "BODY-1405-v1",
        },
    }
    result = compute(payload, kb)
    assert result.payable == D(100)
    assert result.fields["franchise"] == D(0)
    assert result.fields["franchise_source_version"] == "BODY-1405-v1"


@pytest.mark.parametrize("repair", [74, 75])
def test_total_loss_below_or_at_75_percent_is_a_classification_conflict(kb, repair):
    result = compute(
        _case(
            "TOTAL_LOSS",
            market=100,
            insured=100,
            repair=repair,
            franchise=10,
        ),
        kb,
    )
    classification = result.fields["classification"]
    assert result.payable is None
    assert result.status == "CLASSIFICATION_CONFLICT"
    assert classification["outcome"] == "CONFLICT"
    assert classification["declared_canonical_branch"] == "TOTAL_LOSS"
    assert classification["derived_branch"] == "PARTIAL_DAMAGE"
    assert classification["confidence"] == 0.85
    assert classification["basis"]


def test_total_loss_one_rial_above_75_percent_matches_and_settles(kb):
    result = compute(
        _case("TOTAL_LOSS", market=100, insured=100, repair=76, franchise=10), kb
    )
    classification = result.fields["classification"]
    assert result.payable == D(90)
    assert classification["outcome"] == "MATCH"
    assert classification["derived_branch"] == "TOTAL_LOSS"
    assert any("75% threshold" in item for item in classification["basis"])


def test_total_loss_threshold_counts_repair_and_rescue_components(kb):
    result = compute(
        _case(
            "TOTAL_LOSS",
            market=100,
            insured=100,
            repair=70,
            rescue_for_threshold=6,
            franchise=10,
        ),
        kb,
    )
    assert result.payable == D(90)
    assert result.fields["combined_for_threshold"] == D(76)
    assert result.fields["threshold_value"] == D(75)
    assert result.fields["classification"]["outcome"] == "MATCH"


def test_declared_total_loss_without_repair_evidence_is_insufficient(kb):
    result = compute(_case("TOTAL_LOSS", market=100, insured=100, franchise=10), kb)
    classification = result.fields["classification"]
    assert result.payable is None
    assert result.status == "CLASSIFICATION_EVIDENCE_REQUIRED"
    assert classification["outcome"] == "INSUFFICIENT_EVIDENCE"
    assert "repair-and-replacement assessment" in result.reason


def test_documented_authorized_override_can_select_declared_total_loss(kb):
    payload = _case("TOTAL_LOSS", market=100, insured=100, franchise=10)
    payload["classification"]["override"] = {
        "authorized": True,
        "actor": "senior-adjuster-17",
        "reason": "destructive inspection made repair estimate unavailable",
        "source": "review-board-record-2026-41",
        "timestamp": "2026-10-02T04:00:00Z",
    }
    result = compute(payload, kb)
    classification = result.fields["classification"]
    assert result.payable == D(90)
    assert classification["outcome"] == "AUTHORIZED_OVERRIDE"
    assert classification["override"]["actor"] == "senior-adjuster-17"
    assert result.fields["total_loss_threshold_override"] is True
    assert "AUTHORIZED_CLASSIFICATION_OVERRIDE" in result.labels
