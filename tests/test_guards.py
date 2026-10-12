"""Guardrail behaviour: the guards must refuse, not silently approximate."""

from __future__ import annotations

from decimal import Decimal

import pytest
from admission_shim import compute

from iran_auto_claim import guards, operators
from iran_auto_claim.case import Case
from iran_auto_claim.engine import CalcResult
from iran_auto_claim.money import D


def _case(branch: str, **inputs):
    if any(key in inputs for key in ("repair", "repair_total", "repair_total_irr")) and not any(
        key in inputs
        for key in (
            "actual_rescue",
            "rescue",
            "rescue_transport_actual_irr",
            "rescue_for_threshold",
            "rescue_for_total_loss_test_irr",
        )
    ):
        inputs["rescue_for_threshold"] = 0
    if branch == "PARTIAL_DAMAGE":
        if not any(key in inputs for key in ("market", "insured")):
            inputs["market"] = 10**12
            inputs["insured"] = 10**12
        if not any(
            key in inputs
            for key in ("depreciation", "depreciable_parts", "parts", "replacement_parts", "battery_loss", "tire_loss")
        ):
            inputs["depreciation"] = 0
    if branch == "TOTAL_LOSS" and any(key in inputs for key in ("salvage", "salvage_value")):
        inputs.setdefault("salvage_disposition", "INSURED_RETAINS")
    franchise = inputs.pop("franchise", None)
    payload = {
        "claim_id": "guard-test",
        "unit": "IRR",
        "classification": {"branch": branch},
        "damage": inputs,
    }
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
        "GLASS_ONLY",
        "THEFT",
    ):
        payload["coverage_gate"] = {"causal_relationship_established": True}
        payload.setdefault("policy", {})["multiple_insurance"] = {
            "state": "NO",
            "prior_compensation": 0,
        }
    if any(key in inputs for key in ("rescue_payable", "actual_rescue", "rescue")):
        payload["calculation_config"] = {"rescue_cap_base": "ASSESSED_GROSS"}
    return payload


# ------------------------------------------------------- Article 8 method guard


def test_whole_car_ratio_input_is_refused(kb):
    result = compute(
        _case(
            "ARTICLE_8_NON_CONVENTIONAL",
            vehicle_value=2500,
            actual_damage=300,
            corresponding_damage=180,
            policy_financial_limit=200,
            whole_car_ratio=0.56,
        ),
        kb,
    )
    assert result.payable is None
    assert result.status == "GUARD_VIOLATION_ARTICLE8_METHOD"
    assert result.fields["guard_violation"] == "G_ARTICLE8_NO_WHOLE_CAR_RATIO"
    assert "G_ARTICLE8_NO_WHOLE_CAR_RATIO" in result.labels


def test_whole_car_ratio_method_in_config_is_refused(kb):
    payload = _case(
        "ARTICLE_8_NON_CONVENTIONAL",
        vehicle_value=2500,
        actual_damage=300,
        corresponding_damage=180,
        policy_financial_limit=200,
    )
    payload["calculation_config"] = {"article8_method": "WHOLE_CAR_RATIO"}
    result = compute(payload, kb)
    assert result.status == "GUARD_VIOLATION_ARTICLE8_METHOD"


def test_check_article8_method_raises_directly():
    case = Case(_case("ARTICLE_8_NON_CONVENTIONAL", article8_whole_car_ratio=0.5))
    with pytest.raises(guards.GuardViolation) as excinfo:
        guards.check_article8_method(case)
    assert excinfo.value.guard_id == "G_ARTICLE8_NO_WHOLE_CAR_RATIO"


def test_article8_without_a_correspondence_assessment_refuses_rather_than_guessing(kb):
    result = compute(
        _case(
            "ARTICLE_8_NON_CONVENTIONAL",
            vehicle_value=2500,
            actual_damage=300,
            policy_financial_limit=200,
        ),
        kb,
    )
    assert result.payable is None
    assert result.blocking_uncertainties == ["U06_ARTICLE8_COMPONENT_CATALOGUE"]


# ----------------------------------------------------------- franchise guards


def test_universal_glass_franchise_is_refused(kb):
    result = compute(
        _case("GLASS_ONLY", glass_endorsement=True, gross=100, glass_franchise_rate=0.20, market=2500, insured=2500),
        kb,
    )
    assert result.payable is None
    assert result.status == "GUARD_VIOLATION_UNIVERSAL_GLASS_FRANCHISE"


def test_percent_franchise_without_a_policy_source_is_refused():
    case = Case(_case("PARTIAL_DAMAGE", gross=100))
    with pytest.raises(guards.GuardViolation) as excinfo:
        guards.check_franchise_source(case, "PERCENT", None)
    assert excinfo.value.guard_id == "G_NO_HARDCODED_FRANCHISE_RATE"


@pytest.mark.parametrize("source", ["POLICY", "ENDORSEMENT", "INSURER_MANUAL"])
def test_percent_franchise_with_a_source_is_accepted(source):
    case = Case(_case("PARTIAL_DAMAGE", gross=100))
    guards.check_franchise_source(case, "PERCENT", source)


def test_absolute_franchise_needs_no_source_check():
    case = Case(_case("PARTIAL_DAMAGE", gross=100))
    guards.check_franchise_source(case, "ABSOLUTE", None)


# ------------------------------------------------- total-loss ordering guards


def test_salvage_is_not_both_deducted_and_transferred(kb):
    result = compute(
        _case(
            "TOTAL_LOSS",
            market=2000,
            insured=2000,
            repair=1600,
            salvage_value=300,
            salvage_disposition="INSURER_TAKES_TITLE",
            franchise=100,
        ),
        kb,
    )
    assert result.fields["salvage_deduction"] == D(0)
    assert "DO_NOT_DEDUCT_SALVAGE_AND_TRANSFER_IT" in result.labels
    assert result.payable == D(1900)


def test_salvage_precedes_franchise_under_the_circular(kb):
    result = compute(
        _case("TOTAL_LOSS", market=2000, insured=2000, repair=1600, salvage_value=300, franchise=100),
        kb,
    )
    assert result.fields["salvage_deduction"] == D(300)
    assert result.fields["base_after_salvage"] == D(1700)
    assert "CIC_CIRC_1400_401_146850_SALVAGE_BEFORE_FRANCHISE" in result.rule_trace
    assert result.payable == D(1600)


def test_unresolved_salvage_disposition_surfaces_an_uncertainty(kb):
    payload = _case("TOTAL_LOSS", market=2000, insured=2000, repair=1600)
    payload["vehicle"] = {"salvage_disposition": "UNRESOLVED"}
    result = compute(payload, kb)
    assert result.payable is None
    assert result.status == "SALVAGE_DISPOSITION_UNRESOLVED"
    assert result.blocking_uncertainties == ["U12_SALVAGE_DISPOSITION"]


def test_underinsurance_is_never_applied_to_an_already_capped_base(kb):
    result = compute(
        _case("TOTAL_LOSS", market=3000, insured=2400, repair=2300, salvage_value=400, franchise=120, rescue_payable=50),
        kb,
    )
    # min(3000, 2400) - 400 - 120 + 50 = 1930; a second 0.8 ratio would give 1544
    assert result.payable == D(1930)
    assert result.payable != D(1544)
    assert "DO_NOT_APPLY_RATIO_TWICE" in result.labels


def test_insured_sum_ceiling_is_enforced(kb):
    result = compute(
        _case(
            "TOTAL_LOSS",
            market=1000,
            insured=1000,
            repair=800,
            salvage_value=100,
            franchise=1000,
        ),
        kb,
    )
    assert result.payable == D(0)


# ------------------------------------------- battery/tire interaction guard


def test_old_battery_and_tires_surface_the_interaction_uncertainty(kb):
    payload = _case(
            "PARTIAL_DAMAGE",
            production_year=1392,
            battery_loss=40,
            battery_new_price=80,
            franchise=2,
    )
    payload["regulatory_snapshot"] = {"iranian_year": 1405}
    result = compute(payload, kb)
    assert result.payable is None
    assert result.status == "BATTERY_TIRE_INTERACTION_UNRESOLVED"
    assert result.blocking_uncertainties == ["U04_BATTERY_TIRE_CAP_VS_DEPRECIATION"]
    assert result.fields["candidate_scenarios"] == [
        "CAP_THEN_DEPRECIATE",
        "DEPRECIATE_THEN_CAP",
        "CAP_ONLY",
    ]


def test_resolving_the_interaction_yields_a_single_number(kb):
    payload = _case(
        "PARTIAL_DAMAGE",
        production_year=1392,
        battery_loss=40,
        battery_new_price=80,
        franchise=2,
    )
    payload["regulatory_snapshot"] = {"iranian_year": 1405}
    payload["damage"]["market"] = 4000
    payload["damage"]["insured"] = 4000
    payload["calculation_config"] = {"battery_tire_depreciation_interaction": "CAP_THEN_DEPRECIATE"}
    result = compute(payload, kb)
    # cap = 0.5 * 80 = 40; rate = min(0.25, 0.05 * 10) = 0.25; dep = 10
    assert result.fields["depreciation"] == D(10)
    assert result.payable == D(28)
    assert result.blocking_uncertainties == []


def test_operator_refuses_the_interaction_directly():
    part = {"category": "TIRE", "assessed_loss": D(100), "new_price": D(200)}
    with pytest.raises(operators.UncertaintyRequired):
        operators.eligible_part_loss(part, 1392, 1405, {"battery_tire_depreciation_interaction": "UNRESOLVED"})
    info = operators.eligible_part_loss(part, 1392, 1405, {"battery_tire_depreciation_interaction": "CAP_ONLY"})
    assert info["depreciation_amount"] == D(0)


@pytest.mark.parametrize(
    ("mode", "expected_after", "expected_effective_depreciation"),
    [
        ("CAP_THEN_DEPRECIATE", 75, 25),
        ("DEPRECIATE_THEN_CAP", 90, 10),
        ("CAP_ONLY", 100, 0),
    ],
)
def test_battery_tire_modes_apply_depreciation_once(
    mode, expected_after, expected_effective_depreciation
):
    part = {"category": "TIRE", "assessed_loss": D(120), "new_price": D(200)}
    info = operators.eligible_part_loss(
        part, 1392, 1405, {"battery_tire_depreciation_interaction": mode}
    )
    assert info["loss_after_depreciation"] == D(expected_after)
    assert info["depreciation_amount"] == D(expected_effective_depreciation)


# ------------------------------------------- uncertainty propagation guard


def test_a_blocking_uncertainty_never_coexists_with_a_single_payable(kb):
    result = compute(
        _case("PARTIAL_DAMAGE", market=4000, insured=3000, gross=400, franchise=40),
        kb,
    )
    assert result.blocking_uncertainties
    assert result.payable is None
    assert result.payable_scenarios
    assert "BLOCKING_UNCERTAINTY_SURFACED" in result.labels


def test_uncertainty_propagation_guard_fires_on_a_fabricated_result():
    bad = CalcResult(payable=Decimal(100))
    bad.block("U01_ARTICLE10_PARTIAL_ORDER")
    with pytest.raises(guards.GuardViolation) as excinfo:
        guards.check_uncertainty_propagation(bad)
    assert excinfo.value.violation_status == "GUARD_VIOLATION_HIDDEN_UNCERTAINTY"


def test_surface_unresolved_order_as_a_scenario_set_not_a_number(kb):
    result = compute(
        _case("PARTIAL_DAMAGE", market=4000, insured=3000, gross=400, depreciation=20, franchise=40),
        kb,
    )
    assert result.status == "ORDER_UNRESOLVED"
    assert result.payable_scenarios == [D(245), D(255)]
