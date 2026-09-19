"""Money and unit handling: 1 toman = 10 IRR, and no silent float coercion."""

from __future__ import annotations

from decimal import Decimal

import pytest

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
    assert money.fmt(D("342.5"), "million_toman") == "342.50 m-toman"
    assert money.fmt(None, "million_toman") == "n/a"
