"""Money and unit handling: 1 toman = 10 IRR, and no silent float coercion."""

from __future__ import annotations

from decimal import Decimal

import pytest
from admission_shim import compute

from iran_auto_claim import money
from iran_auto_claim.money import D


def test_decimals_never_pass_through_binary_floats():
    assert D(0.1) == Decimal("0.1")
    assert D("0.1") == Decimal("0.1")
    assert D(37.5) == Decimal("37.5")
    assert D(10) == Decimal(10)
    assert D(Decimal("2.5")) == Decimal("2.5")


def test_booleans_are_not_money():
    with pytest.raises(money.UnitError):
        D(True)


def test_uninterpretable_values_are_refused():
    with pytest.raises(money.UnitError):
        D(object())


@pytest.mark.parametrize(
    "unit,amount,expected_irr",
    [
        ("IRR", 1_000_000_000, 1_000_000_000),
        ("toman", 1_000_000_000, 10_000_000_000),
        ("million_toman", 1, 10_000_000),
        ("billion_toman", 1, 10_000_000_000),
    ],
)
def test_unit_conversion_uses_ten_rial_to_the_toman(unit, amount, expected_irr):
    assert money.to_irr(D(amount), unit) == Decimal(expected_irr)


def test_unit_conversion_round_trips():
    for unit in money.UNITS:
        original = D(1_234_567)
        assert money.from_irr(money.to_irr(original, unit), unit) == original


def test_annual_parameter_threshold_converts_into_the_case_unit():
    """The 1405 threshold must land at 1400 million tomans, not 1.4e10 tomans."""
    threshold_irr = D(14_000_000_000)
    assert money.from_irr(threshold_irr, "million_toman") == D(1400)
    assert money.from_irr(threshold_irr, "IRR") == D(14_000_000_000)
    assert money.from_irr(threshold_irr, "toman") == D(1_400_000_000)


def test_unknown_units_are_refused():
    with pytest.raises(money.UnitError):
        money.to_irr(D(1), "rial")
    with pytest.raises(money.UnitError):
        money.from_irr(D(1), "kilogram")


def test_formatting_is_stable():
    assert money.fmt(D("3425000000"), "million_toman") == "342.50 m-toman"
    assert money.fmt(None, "million_toman") == "n/a"


@pytest.mark.parametrize(
    ("display", "expected"),
    [("0.00000004", 0), ("0.00000005", 1), ("0.00000006", 1)],
)
def test_explicit_display_conversion_rounds_half_up_to_one_rial(display, expected):
    assert money.to_irr(D(display), "million_toman") == D(expected)


def test_final_payable_rounds_half_up_once_at_the_engine_boundary(kb):
    result = compute(
        {
            "claim_id": "ROUND-HALF-UP",
            "unit": "IRR",
            "classification": {"branch": "PARTIAL_DAMAGE"},
            "damage": {"gross": 5, "depreciation": 0, "market": 5, "insured": 5},
            "coverage_gate": {"causal_relationship_established": True},
            "policy": {
                "multiple_insurance": {"state": "NO", "prior_compensation": 0},
                "franchise": {
                    "mode": "PERCENT",
                    "rate": 0.5,
                    "calculation_base": "AFTER_DEPRECIATION",
                    "source": "POLICY",
                }
            },
        },
        kb,
    )
    assert result.fields["franchise"] == D("2.5")
    assert result.payable == D(3)


def test_scenario_order_survives_irr_rounding_and_json_has_no_decimal_float(kb):
    result = compute(
        {
            "claim_id": "ROUND-SCENARIOS",
            "unit": "IRR",
            "classification": {"branch": "PARTIAL_DAMAGE"},
            "damage": {"gross": 10, "depreciation": 0, "market": 3, "insured": 1},
            "coverage_gate": {"causal_relationship_established": True},
            "policy": {
                "policy_version": "TEST-v1",
                "multiple_insurance": {"state": "NO", "prior_compensation": 0},
                "franchise": {
                    "mode": "ABSOLUTE",
                    "absolute_irr": 1,
                    "source": "POLICY",
                    "source_reference": "test policy schedule",
                    "source_version": "TEST-v1",
                },
            },
        },
        kb,
    )
    assert result.payable_scenarios == [D(2), D(3)]
    document = result.to_dict()
    assert document["unit"] == "IRR"
    assert document["payable_scenarios_irr"] == [2, 3]
    assert isinstance(document["fields"]["article10_ratio"], str)
    assert document["fields"]["article10_ratio"].startswith("0.333333")


def test_result_serialization_never_coerces_nested_decimals_to_float():
    from iran_auto_claim.engine import CalcResult

    result = CalcResult(fields={"nested": {"ratio": D("0.125")}, "items": [D(7)]})
    document = result.to_dict()
    assert document["fields"]["nested"]["ratio"] == "0.125"
    assert document["fields"]["items"] == [7]


def test_very_large_integer_irr_does_not_overflow(kb):
    amount = 10**100
    result = compute(
        {
            "claim_id": "LARGE-IRR",
            "unit": "IRR",
            "classification": {"branch": "PARTIAL_DAMAGE"},
            "coverage_gate": {"causal_relationship_established": True},
            "damage": {
                "gross": amount,
                "depreciation": 0,
                "market": amount,
                "insured": amount,
            },
            "policy": {
                "policy_version": "TEST-v1",
                "multiple_insurance": {"state": "NO", "prior_compensation": 0},
                "franchise": {
                    "mode": "ABSOLUTE",
                    "absolute_irr": 0,
                    "source": "POLICY",
                    "source_reference": "test declarations page",
                    "source_version": "TEST-v1",
                },
            },
        },
        kb,
    )
    assert result.payable == D(amount)
    assert result.to_dict()["payable_irr"] == amount
