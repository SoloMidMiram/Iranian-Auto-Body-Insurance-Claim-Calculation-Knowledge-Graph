"""Engine-level behaviour: classification, dispatch, confidence, refusals."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from admission_shim import compute

from iran_auto_claim.classify import classify
from iran_auto_claim.engine import _dated_theft_clock_days
from iran_auto_claim.money import D
from iran_auto_claim.schema_input import InputSchemaError


def _case(branch=None, **inputs):
    if any(key in inputs for key in ("repair", "repair_total", "repair_total_irr")) and not any(
        key in inputs
        for key in (
            "actual_rescue",
            "rescue",
            "rescue_transport_actual_irr",
            "rescue_for_threshold",
            "rescue_for_total_loss_test_irr",
            "rescue_omission_legacy_compatibility",
        )
    ):
        inputs["rescue_for_threshold"] = 0
    if branch in ("PARTIAL_DAMAGE", "THEFT_PARTIAL_DAMAGE"):
        if not any(key in inputs for key in ("market", "market_value", "insured", "insured_sum")):
            inputs["market"] = 10**12
            inputs["insured"] = 10**12
        if not any(
            key in inputs
            for key in (
                "depreciation",
                "assessed_depreciation_irr",
                "depreciable_parts",
                "parts",
                "replacement_parts",
                "battery_loss",
                "tire_loss",
                "lamp_glass",
                "other_replacement_part",
            )
        ):
            inputs["depreciation"] = 0
    if branch == "GLASS_ONLY" and not any(
        key in inputs for key in ("market", "market_value", "insured", "insured_sum")
    ):
        inputs["market"] = 10**12
        inputs["insured"] = 10**12
    if branch in ("TOTAL_LOSS", "TOTAL_LOSS_TEST") and any(
        key in inputs for key in ("salvage", "salvage_value")
    ):
        inputs.setdefault("salvage_disposition", "INSURED_RETAINS")
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
    if branch in (
        "PARTIAL_DAMAGE",
        "TOTAL_LOSS",
        "TOTAL_LOSS_TEST",
        "GLASS_ONLY",
        "THEFT",
        "TOTAL_THEFT",
        "THEFT_PARTIAL_DAMAGE",
    ):
        payload["coverage_gate"] = {"causal_relationship_established": True}
        payload.setdefault("policy", {})["multiple_insurance"] = {
            "state": "NO",
            "prior_compensation": 0,
        }
    if branch:
        payload["classification"] = {"branch": branch}
    if branch in ("THEFT", "TOTAL_THEFT") and inputs.get("theft_type") == "WHOLE_VEHICLE":
        days = int(inputs.get("days_missing", inputs.get("days_vehicle_missing", 0)))
        payload["event"] = {
            "event_date": "2026-01-01",
            "theft_clock": {
                "start_event": "THEFT_OCCURRENCE",
                "start_date": "2026-01-01",
                "as_of_date": (date(2026, 1, 1) + timedelta(days=days)).isoformat(),
                "calendar": "GREGORIAN",
                "source": "synthetic test police report",
            }
        }
    return payload


# --------------------------------------------------------------- classifier


def test_classifier_routes_total_loss():
    verdict = classify(_case("TOTAL_LOSS", market=2000, repair=1600))
    assert verdict["branch"] == "TOTAL_LOSS"


@pytest.mark.parametrize("causation", [False, None])
def test_engine_blocks_unestablished_positive_covered_peril_causation(causation, kb):
    payload = _case("PARTIAL_DAMAGE", gross=100, franchise=0)
    if causation is None:
        payload.pop("coverage_gate")
    else:
        payload["coverage_gate"]["causal_relationship_established"] = causation

    result = compute(payload, kb)

    assert result.payable is None
    assert result.status == "COVERED_PERIL_CAUSATION_REQUIRED"
    assert result.fields["guard_violation"] == (
        "G_COVERED_PERIL_CAUSATION_ESTABLISHED"
    )


@pytest.mark.parametrize(
    ("multiple_insurance", "status"),
    [
        (None, "RECOVERY_FACTS_REQUIRED"),
        ({"state": "UNKNOWN", "prior_compensation": 0}, "RECOVERY_FACTS_REQUIRED"),
        ({"state": "NO", "prior_compensation": 1}, "PRIOR_COMPENSATION_SETTLEMENT_UNSUPPORTED"),
        ({"state": "YES_OTHER_POLICIES", "prior_compensation": 0}, "MULTIPLE_INSURANCE_CONTRIBUTION_NOT_IMPLEMENTED"),
        ({"state": "YES_SAME_INSURER", "prior_compensation": 0}, "MULTIPLE_INSURANCE_CONTRIBUTION_NOT_IMPLEMENTED"),
    ],
)
def test_engine_blocks_unsupported_recovery_and_multiple_policy_states(
    multiple_insurance, status, kb
):
    payload = _case("PARTIAL_DAMAGE", gross=100, franchise=0)
    if multiple_insurance is None:
        payload["policy"].pop("multiple_insurance")
    else:
        payload["policy"]["multiple_insurance"] = multiple_insurance

    result = compute(payload, kb)

    assert result.payable is None
    assert result.status == status
    assert result.fields["guard_violation"] == "G_RECOVERY_ALLOCATION_CONTAINED"
    recovery_guard = kb.guards["G_RECOVERY_ALLOCATION_CONTAINED"]
    assert result.status in recovery_guard["violation_statuses"]
    assert recovery_guard["triggered_label"] in result.labels


def test_recovery_guard_declares_every_runtime_status(kb):
    recovery_guard = kb.guards["G_RECOVERY_ALLOCATION_CONTAINED"]

    assert set(recovery_guard["violation_statuses"]) == {
        "RECOVERY_FACTS_REQUIRED",
        "PRIOR_COMPENSATION_SETTLEMENT_UNSUPPORTED",
        "MULTIPLE_INSURANCE_CONTRIBUTION_NOT_IMPLEMENTED",
    }


def test_engine_records_the_two_new_admission_guards_on_a_valid_control(kb):
    result = compute(_case("PARTIAL_DAMAGE", gross=100, franchise=0), kb)

    assert result.payable == D(100)
    assert result.fields["covered_peril_causation_established"] is True
    assert result.fields["multiple_insurance_state"] == "NO"
    assert result.fields["prior_compensation"] == D(0)
    assert "G_COVERED_PERIL_CAUSATION_ESTABLISHED" in result.guards_executed
    assert "G_RECOVERY_ALLOCATION_CONTAINED" in result.guards_executed


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


def test_intoxication_exclusion_requires_both_coded_cause_and_causal_finding(kb):
    payload = _case(
        "PARTIAL_DAMAGE",
        gross=100,
        depreciation=0,
        market=100,
        insured=100,
        franchise=10,
        cause="ALCOHOL",
    )
    not_confirmed = compute(payload, kb)
    assert not_confirmed.payable == D(90)
    assert "exclusion_applied" not in not_confirmed.fields

    payload["event"] = {"intoxication_causally_confirmed": True}
    confirmed = compute(payload, kb)
    assert confirmed.payable == D(0)
    assert confirmed.fields["exclusion_applied"] == "EX_INTOXICATION"


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


def test_missing_both_article10_value_anchors_does_not_default_ratio_to_one(kb):
    payload = {
        "claim_id": "missing-economic-anchors",
        "unit": "IRR",
        "classification": {"branch": "PARTIAL_DAMAGE"},
        "damage": {"gross": 100, "depreciation": 0},
        "coverage_gate": {"causal_relationship_established": True},
        "policy": {
            "policy_version": "TEST-v1",
            "multiple_insurance": {"state": "NO", "prior_compensation": 0},
            "franchise": {
                "mode": "ABSOLUTE",
                "absolute_irr": 10,
                "source": "POLICY",
                "source_reference": "test schedule",
                "source_version": "TEST-v1",
            },
        },
    }
    result = compute(payload, kb)
    assert result.status == "INPUT_ERROR"
    assert result.payable is None
    assert "market value and insured sum" in result.reason


def test_aggregate_partial_damage_does_not_default_missing_depreciation_to_zero(kb):
    payload = _case(
        "PARTIAL_DAMAGE", gross=100, market=100, insured=100, franchise=10
    )
    payload["damage"].pop("depreciation")
    result = compute(payload, kb)
    assert result.status == "INPUT_ERROR"
    assert result.payable is None
    assert "explicit assessed depreciation" in result.reason


def test_total_loss_settlement_requires_both_figures(kb):
    payload = _case("TOTAL_LOSS", market=2000, repair=1600, salvage_value=300, franchise=100)
    result = compute(payload, kb)
    assert result.status == "INPUT_ERROR"


def test_salvage_value_without_disposition_blocks_total_loss_settlement(kb):
    payload = _case(
        "TOTAL_LOSS",
        market=2000,
        insured=2000,
        repair=1600,
        salvage=300,
        franchise=100,
    )
    payload["damage"].pop("salvage_disposition")
    result = compute(payload, kb)
    assert result.status == "SALVAGE_DISPOSITION_UNRESOLVED"
    assert result.blocking_uncertainties == ["U12_SALVAGE_DISPOSITION"]


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


def test_whole_theft_requires_a_bound_clock_and_matching_day_count(kb):
    payload = _case(
        "THEFT",
        theft_type="WHOLE_VEHICLE",
        days_missing=65,
        market=2200,
        insured=2200,
        franchise=220,
        title_transferred=True,
    )
    clock = payload.pop("event")
    unanchored = compute(payload, kb)
    assert unanchored.status == "THEFT_CLOCK_ANCHOR_UNRESOLVED"
    assert unanchored.blocking_uncertainties == ["U13_THEFT_CLOCK_ANCHOR"]

    payload["event"] = clock
    payload["damage"]["days_missing"] = 64
    mismatch = compute(payload, kb)
    assert mismatch.status == "INPUT_ERROR"
    assert "does not match the bound theft clock" in mismatch.reason


def _whole_theft_with_clock(
    *, start: str, as_of: str, days: int, calendar: str = "SHAMSI"
) -> dict:
    payload = _case(
        "THEFT",
        theft_type="WHOLE_VEHICLE",
        days_missing=days,
        market=2200,
        insured=2200,
        franchise=220,
        title_transferred=True,
    )
    payload["event"] = {
        "event_date": start,
        "theft_clock": {
            "start_event": "THEFT_OCCURRENCE",
            "start_date": start,
            "as_of_date": as_of,
            "calendar": calendar,
            "source": "synthetic dated police record",
        }
    }
    return payload


@pytest.mark.parametrize(
    ("start_event", "event_date_field"),
    [
        ("THEFT_OCCURRENCE", "event_date"),
        ("AWARENESS", "awareness_date"),
        ("DECLARATION", "declaration_date"),
    ],
)
def test_theft_clock_start_date_is_bound_to_selected_event(
    kb, start_event, event_date_field
):
    payload = _whole_theft_with_clock(
        start="1403-01-01", as_of="1403-02-29", days=59
    )
    payload["event"][event_date_field] = "1403-01-01"
    payload["event"]["theft_clock"]["start_event"] = start_event

    accepted = compute(payload, kb)
    assert accepted.status == "PENDING_60_DAY_CRITERION"

    payload["event"][event_date_field] = "1403-01-02"
    rejected = compute(payload, kb)
    assert rejected.status == "INPUT_ERROR"
    assert f"event.{event_date_field} (1403-01-02)" in rejected.reason


@pytest.mark.parametrize("event_date", ["1403/01/01", "2024-03-20"])
def test_theft_clock_start_date_matches_selected_event_by_calendar_value(
    kb, event_date
):
    payload = _whole_theft_with_clock(
        start="1403-01-01", as_of="1403-02-29", days=59
    )
    payload["event"]["event_date"] = event_date

    result = compute(payload, kb)

    assert result.status == "PENDING_60_DAY_CRITERION"
    assert result.fields["theft_clock"]["derived_days"] == 59


def test_theft_clock_requires_the_selected_event_date(kb):
    payload = _whole_theft_with_clock(
        start="1403-01-01", as_of="1403-02-29", days=59
    )
    payload["event"]["theft_clock"]["start_event"] = "DECLARATION"

    result = compute(payload, kb)

    assert result.status == "THEFT_CLOCK_ANCHOR_UNRESOLVED"
    assert result.payable is None
    assert result.blocking_uncertainties == ["U13_THEFT_CLOCK_ANCHOR"]


def test_shamsi_leap_year_accepts_esfand_30(kb):
    result = compute(
        _whole_theft_with_clock(
            start="1403-12-30", as_of="1404-01-01", days=1
        ),
        kb,
    )
    assert result.status == "PENDING_60_DAY_CRITERION"
    assert result.fields["theft_clock"]["derived_days"] == 1


def test_shamsi_non_leap_year_rejects_esfand_30(kb):
    with pytest.raises(InputSchemaError) as caught:
        compute(
            _whole_theft_with_clock(
                start="1402-12-30", as_of="1403-01-01", days=1
            ),
            kb,
        )
    assert any(item.code == "invalid_date" for item in caught.value.errors)


@pytest.mark.parametrize(
    ("days", "as_of", "status", "payable"),
    [
        (59, "1403-02-29", "PENDING_60_DAY_CRITERION", None),
        (60, "1403-02-30", None, D(1980)),
        (61, "1403-02-31", None, D(1980)),
    ],
)
def test_shamsi_theft_clock_59_60_61_day_boundaries(
    kb, days, as_of, status, payable
):
    result = compute(
        _whole_theft_with_clock(start="1403-01-01", as_of=as_of, days=days),
        kb,
    )
    assert result.fields["theft_clock"]["derived_days"] == days
    assert result.status == status
    assert result.payable == payable


def test_cross_year_shamsi_interval_matches_equivalent_gregorian_interval():
    shamsi = _dated_theft_clock_days(
        {
            "start_date": "1403-12-29",
            "as_of_date": "1404-01-01",
            "calendar": "SHAMSI",
        }
    )
    gregorian = _dated_theft_clock_days(
        {
            "start_date": "2025-03-19",
            "as_of_date": "2025-03-21",
            "calendar": "GREGORIAN",
        }
    )
    assert shamsi == gregorian == 2


def test_shamsi_theft_clock_rejects_stored_day_mismatch(kb):
    result = compute(
        _whole_theft_with_clock(
            start="1403-01-01", as_of="1403-02-31", days=60
        ),
        kb,
    )
    assert result.status == "INPUT_ERROR"
    assert "does not match the bound theft clock (61)" in result.reason


def test_shamsi_theft_clock_rejects_as_of_before_start(kb):
    with pytest.raises(InputSchemaError) as caught:
        compute(
            _whole_theft_with_clock(
                start="1403-02-01", as_of="1403-01-31", days=0
            ),
            kb,
        )
    assert any(
        item.code == "invalid_chronology"
        and item.path == "event.theft_clock.as_of_date"
        for item in caught.value.errors
    )


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("start_date", "1403/01/01", "invalid_type"),
        ("calendar", "LUNAR", "invalid_enum"),
    ],
)
def test_theft_clock_schema_rejects_malformed_date_or_calendar(kb, field, value, code):
    payload = _whole_theft_with_clock(
        start="1403-01-01", as_of="1403-02-30", days=60
    )
    payload["event"]["theft_clock"][field] = value
    with pytest.raises(InputSchemaError) as caught:
        compute(payload, kb)
    assert any(
        item.path == f"event.theft_clock.{field}" and item.code == code
        for item in caught.value.errors
    )


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


def test_actual_and_payable_rescue_operands_remain_distinct_through_calculation(kb):
    actual_only = _case(
        "PARTIAL_DAMAGE", gross=1000, franchise=0, actual_rescue=300
    )
    actual_only["calculation_config"] = {"rescue_cap_base": "ASSESSED_GROSS"}
    actual_result = compute(actual_only, kb)
    assert actual_result.fields["rescue_input_kind"] == "ACTUAL"
    assert actual_result.fields["rescue_claimed"] == D(300)
    assert actual_result.fields["rescue_payable_supplied"] is None
    assert actual_result.fields["allowable_rescue_transport"] == D(200)

    payable_only = _case(
        "PARTIAL_DAMAGE", gross=1000, franchise=0, rescue_payable=150
    )
    payable_only["calculation_config"] = {"rescue_cap_base": "ASSESSED_GROSS"}
    payable_result = compute(payable_only, kb)
    assert payable_result.fields["rescue_input_kind"] == "PAYABLE"
    assert payable_result.fields["rescue_claimed"] is None
    assert payable_result.fields["rescue_payable_supplied"] == D(150)
    assert payable_result.fields["allowable_rescue_transport"] == D(150)

    both = _case(
        "PARTIAL_DAMAGE",
        gross=1000,
        franchise=0,
        actual_rescue=300,
        rescue_payable=150,
    )
    both["calculation_config"] = {"rescue_cap_base": "ASSESSED_GROSS"}
    both_result = compute(both, kb)
    assert both_result.fields["rescue_input_kind"] == "ACTUAL_AND_PAYABLE"
    assert both_result.fields["rescue_claimed"] == D(300)
    assert both_result.fields["rescue_payable_supplied"] == D(150)
    assert both_result.fields["allowable_rescue_transport"] == D(150)

    classified = _case(
        "PARTIAL_DAMAGE",
        market=10000,
        insured=10000,
        gross=7000,
        repair=7000,
        actual_rescue=300,
        rescue_payable=150,
        franchise=0,
    )
    classified["calculation_config"] = {"rescue_cap_base": "ASSESSED_GROSS"}
    classified_result = compute(classified, kb)
    assert classified_result.fields["classification_rescue"] == D(300)
    assert (
        classified_result.fields["classification_rescue_source"]
        == "DERIVED_FROM_ACTUAL_RESCUE"
    )
    assert classified_result.fields["allowable_rescue_transport"] == D(150)


def test_supplied_rescue_payable_above_actual_or_ceiling_is_refused(kb):
    above_actual = _case(
        "PARTIAL_DAMAGE",
        gross=1000,
        franchise=0,
        actual_rescue=100,
        rescue_payable=150,
    )
    above_actual["calculation_config"] = {"rescue_cap_base": "ASSESSED_GROSS"}
    result = compute(above_actual, kb)
    assert result.status == "INPUT_ERROR"
    assert "exceeds the separately supplied actual expense" in result.reason

    above_ceiling = _case(
        "PARTIAL_DAMAGE", gross=1000, franchise=0, rescue_payable=201
    )
    above_ceiling["calculation_config"] = {"rescue_cap_base": "ASSESSED_GROSS"}
    result = compute(above_ceiling, kb)
    assert result.status == "INPUT_ERROR"
    assert "exceeds the applicable rescue ceiling" in result.reason


def test_material_rescue_denominator_difference_blocks_when_base_is_missing(kb):
    payload = _case(
        "PARTIAL_DAMAGE",
        gross=1000,
        depreciation=900,
        market=1000,
        insured=1000,
        actual_rescue=100,
        franchise=0,
    )
    result = compute(payload, kb)
    assert result.payable is None
    assert result.status == "RESCUE_DENOMINATOR_UNRESOLVED"
    assert result.blocking_uncertainties == ["U05_RESCUE_DENOMINATOR"]


def test_zero_supplied_rescue_does_not_block_on_non_positive_candidate_base(kb):
    payload = _case(
        "PARTIAL_DAMAGE",
        gross=100,
        depreciation=120,
        market=100,
        insured=100,
        rescue_payable=0,
        franchise=0,
    )

    result = compute(payload, kb)

    assert result.status is None
    assert result.payable == D(0)
    assert result.fields["allowable_rescue_transport"] == D(0)
    assert result.fields["rescue_payable_supplied"] == D(0)
    assert result.blocking_uncertainties == []


def test_positive_supplied_rescue_still_blocks_on_material_candidate_difference(kb):
    payload = _case(
        "PARTIAL_DAMAGE",
        gross=1000,
        depreciation=900,
        market=1000,
        insured=1000,
        rescue_payable=100,
        franchise=0,
    )

    result = compute(payload, kb)

    assert result.payable is None
    assert result.status == "RESCUE_DENOMINATOR_UNRESOLVED"
    assert result.fields["rescue_candidate_amounts"] == {
        "ASSESSED_GROSS": D(100),
        "ELIGIBLE_GROSS": D(100),
        "SETTLEMENT_BASE": D(20),
    }
    assert result.blocking_uncertainties == ["U05_RESCUE_DENOMINATOR"]


def test_percentage_franchise_uses_the_named_base(kb):
    payload = _case(
        "PARTIAL_DAMAGE", gross=100, depreciation=20, market=100, insured=100
    )
    payload["policy"] = {
        "policy_version": "TEST-v1",
        "multiple_insurance": {"state": "NO", "prior_compensation": 0},
        "franchise": {
            "mode": "PERCENT",
            "rate": 0.1,
            "calculation_base": "ASSESSED_GROSS",
            "source": "POLICY",
            "source_reference": "test schedule",
            "source_version": "TEST-v1",
        },
    }
    assessed = compute(payload, kb)
    assert assessed.fields["franchise"] == D(10)
    assert assessed.payable == D(70)

    payload["policy"]["franchise"]["calculation_base"] = "AFTER_DEPRECIATION"
    after_depreciation = compute(payload, kb)
    assert after_depreciation.fields["franchise"] == D(8)
    assert after_depreciation.payable == D(72)


def test_missing_percentage_franchise_base_is_rejected_instead_of_using_branch_default(kb):
    payload = _case(
        "PARTIAL_DAMAGE", gross=100, depreciation=0, market=100, insured=100
    )
    payload["policy"] = {
        "policy_version": "TEST-v1",
        "multiple_insurance": {"state": "NO", "prior_compensation": 0},
        "franchise": {
            "mode": "PERCENT",
            "rate": 0.1,
            "source": "POLICY",
            "source_reference": "test schedule",
            "source_version": "TEST-v1",
        },
    }
    with pytest.raises(InputSchemaError) as caught:
        compute(payload, kb)
    assert any(
        item.path == "policy.franchise.calculation_base" and item.code == "missing_field"
        for item in caught.value.errors
    )


def _total_loss_with_percentage_franchise(calculation_base: str | None) -> dict:
    payload = _case(
        "TOTAL_LOSS",
        market=2000,
        insured=2000,
        repair=1600,
        salvage=300,
        salvage_disposition="INSURED_RETAINS",
    )
    franchise = {
        "mode": "PERCENT",
        "rate": 0.1,
        "source": "POLICY",
        "source_reference": "total-loss test schedule",
        "source_version": "TEST-v1",
    }
    if calculation_base is not None:
        franchise["calculation_base"] = calculation_base
    payload["policy"] = {
        "policy_version": "TEST-v1",
        "multiple_insurance": {"state": "NO", "prior_compensation": 0},
        "franchise": franchise,
    }
    return payload


def test_total_loss_percentage_franchise_distinguishes_settlement_base_from_after_salvage(kb):
    settlement_base = compute(
        _total_loss_with_percentage_franchise("SETTLEMENT_BASE"), kb
    )
    after_salvage = compute(
        _total_loss_with_percentage_franchise("AFTER_SALVAGE"), kb
    )

    assert settlement_base.fields["settlement_base"] == D(2000)
    assert settlement_base.fields["base_after_salvage"] == D(1700)
    assert settlement_base.fields["franchise_calculation_base"] == D(2000)
    assert settlement_base.fields["franchise"] == D(200)
    assert settlement_base.payable == D(1500)

    assert after_salvage.fields["settlement_base"] == D(2000)
    assert after_salvage.fields["base_after_salvage"] == D(1700)
    assert after_salvage.fields["franchise_calculation_base"] == D(1700)
    assert after_salvage.fields["franchise"] == D(170)
    assert after_salvage.payable == D(1530)

    assert settlement_base.fields["franchise"] != after_salvage.fields["franchise"]


@pytest.mark.parametrize("calculation_base", ["SETTLEMENT_BASE", "AFTER_SALVAGE"])
def test_total_loss_title_transfer_makes_salvage_deduction_zero(kb, calculation_base):
    payload = _total_loss_with_percentage_franchise(calculation_base)
    payload["damage"]["salvage_disposition"] = "INSURER_TAKES_TITLE"
    result = compute(payload, kb)

    assert result.fields["salvage_deduction"] == D(0)
    assert result.fields["settlement_base"] == D(2000)
    assert result.fields["base_after_salvage"] == D(2000)
    assert result.fields["franchise_calculation_base"] == D(2000)
    assert result.fields["franchise"] == D(200)
    assert result.payable == D(1800)


def test_total_loss_percentage_franchise_rejects_an_unsupported_base(kb):
    payload = _total_loss_with_percentage_franchise("AFTER_UNDERINSURANCE")
    with pytest.raises(InputSchemaError) as caught:
        compute(payload, kb)
    assert any(
        item.path == "policy.franchise.calculation_base" and item.code == "invalid_enum"
        for item in caught.value.errors
    )


def test_total_loss_percentage_franchise_requires_a_named_base(kb):
    payload = _total_loss_with_percentage_franchise(None)
    with pytest.raises(InputSchemaError) as caught:
        compute(payload, kb)
    assert any(
        item.path == "policy.franchise.calculation_base" and item.code == "missing_field"
        for item in caught.value.errors
    )


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


def test_article8_zero_actual_damage_is_not_replaced_by_the_corresponding_cap(kb):
    result = compute(
        _case(
            "ARTICLE_8_NON_CONVENTIONAL",
            vehicle_value=2500,
            actual_damage=0,
            corresponding_damage=180,
            tp_limit=200,
        ),
        kb,
    )
    assert result.fields["actual_damage"] == D(0)
    assert result.payable == D(0)


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
        "multiple_insurance": {"state": "NO", "prior_compensation": 0},
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
        "multiple_insurance": {"state": "NO", "prior_compensation": 0},
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


def test_unequal_actual_and_classification_rescue_needs_accepted_interpretation(kb):
    result = compute(
        _case(
            "PARTIAL_DAMAGE",
            market=10000,
            insured=10000,
            repair=7400,
            actual_rescue=200,
            rescue_for_threshold=100,
            franchise=0,
        ),
        kb,
    )
    assert result.payable is None
    assert result.status == "CLASSIFICATION_EVIDENCE_REQUIRED"
    assert result.fields["classification"]["outcome"] == "INSUFFICIENT_EVIDENCE"
    assert "applicable authority" in result.reason


def test_embedded_rescue_must_be_decomposed_before_threshold_addition(kb):
    result = compute(
        _case(
            "PARTIAL_DAMAGE",
            market=10000,
            insured=10000,
            repair=7400,
            actual_rescue=200,
            repair_total_includes_rescue=True,
            franchise=0,
        ),
        kb,
    )
    assert result.payable is None
    assert result.status == "CLASSIFICATION_EVIDENCE_REQUIRED"
    assert "evidenced decomposition" in result.reason


@pytest.mark.parametrize("declared_branch", [True, False])
def test_missing_material_rescue_blocks_internal_partial_payment(kb, declared_branch):
    payload = _case(
        "PARTIAL_DAMAGE",
        market=10000,
        insured=10000,
        gross=7400,
        repair=7400,
        franchise=0,
    )
    payload["damage"].pop("rescue_for_threshold")
    if not declared_branch:
        payload["classification"].pop("branch")
    result = compute(payload, kb)
    assert result.payable is None
    assert result.status == "CLASSIFICATION_EVIDENCE_REQUIRED"
    assert result.fields["classification"]["outcome"] == "INSUFFICIENT_EVIDENCE"
    assert "preliminary zero cannot authorize payment" in result.reason


def test_missing_material_rescue_cannot_be_overridden_into_payment(kb):
    payload = _case(
        "PARTIAL_DAMAGE",
        market=10000,
        insured=10000,
        gross=7400,
        repair=7400,
        franchise=0,
    )
    payload["damage"].pop("rescue_for_threshold")
    payload["classification"]["override"] = {
        "authorized": True,
        "actor": "senior-adjuster-17",
        "reason": "documented partial-loss branch selection",
        "source": "review-board-record-2026-42",
        "timestamp": "2026-10-12T04:00:00Z",
    }

    result = compute(payload, kb)

    assert result.payable is None
    assert result.status == "CLASSIFICATION_EVIDENCE_REQUIRED"
    assert result.fields["classification"]["outcome"] == "INSUFFICIENT_EVIDENCE"
    assert "preliminary zero cannot authorize payment" in result.reason


def test_missing_classification_rescue_does_not_block_whole_vehicle_theft(kb):
    payload = _case(
        "THEFT",
        theft_type="WHOLE_VEHICLE",
        days_missing=65,
        market=10000,
        insured=10000,
        repair=7400,
        franchise=1000,
        title_transferred=True,
        salvage_disposition="INSURER_TAKES_TITLE",
    )
    payload["damage"].pop("rescue_for_threshold")

    result = compute(payload, kb)

    assert result.payable == D(9000)
    assert result.fields["classification"]["outcome"] == "MATCH"
    assert result.fields["classification"]["derived_branch"] == "THEFT"
    assert not any(
        "75% threshold" in item
        for item in result.fields["classification"]["basis"]
    )


def test_omitted_rescue_needs_explicit_legacy_compatibility(kb):
    payload = _case(
        "PARTIAL_DAMAGE",
        market=10000,
        insured=10000,
        gross=7400,
        repair=7400,
        rescue_omission_legacy_compatibility=True,
        franchise=0,
    )
    result = compute(payload, kb)
    assert result.payable == D(7400)
    assert result.fields["classification_rescue"] == D(0)
    assert (
        result.fields["classification_rescue_source"]
        == "EXPLICIT_LEGACY_DEFAULT_ZERO"
    )


def test_declared_total_loss_without_repair_evidence_is_insufficient(kb):
    result = compute(_case("TOTAL_LOSS", market=100, insured=100, franchise=10), kb)
    classification = result.fields["classification"]
    assert result.payable is None
    assert result.status == "CLASSIFICATION_EVIDENCE_REQUIRED"
    assert classification["outcome"] == "INSUFFICIENT_EVIDENCE"
    assert "repair-and-replacement assessment" in result.reason


def test_documented_authorized_override_can_select_declared_total_loss_with_complete_operands(
    kb,
):
    payload = _case(
        "TOTAL_LOSS", market=100, insured=100, repair=74, franchise=10
    )
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
