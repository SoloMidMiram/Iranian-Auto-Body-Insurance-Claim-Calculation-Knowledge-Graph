"""Operator-level unit tests: the formulas and the refusals."""

from __future__ import annotations

from decimal import Decimal

import pytest

from iran_auto_claim import operators
from iran_auto_claim.money import D


# ------------------------------------------------------------------ ratio


@pytest.mark.parametrize(
    "insured,market,expected",
    [
        (3000, 3000, "1"),
        (4000, 3000, "1"),  # over-insured: capped at 1, never a windfall multiplier
        (3000, 4000, "0.75"),
        (2000, 4000, "0.5"),
        (0, 4000, "0"),
    ],
)
def test_underinsurance_ratio(insured, market, expected):
    assert operators.underinsurance_ratio(D(insured), D(market)) == Decimal(expected)


def test_underinsurance_requires_both_figures():
    with pytest.raises(operators.OperatorError):
        operators.underinsurance_ratio(None, D(1000))
    with pytest.raises(operators.OperatorError):
        operators.underinsurance_ratio(D(1000), None)
    with pytest.raises(operators.OperatorError):
        operators.underinsurance_ratio(D(1000), D(0))


# ----------------------------------------------------------- depreciation


@pytest.mark.parametrize(
    "production_year,claim_year,category,expected",
    [
        (1405, 1405, "OTHER_REPLACEMENT_PART", "0"),  # production year index 1
        (1402, 1405, "OTHER_REPLACEMENT_PART", "0"),  # index 4: still free
        (1401, 1405, "OTHER_REPLACEMENT_PART", "0.05"),  # index 5: fifth year starts at 5%
        (1400, 1405, "OTHER_REPLACEMENT_PART", "0.10"),
        (1399, 1405, "OTHER_REPLACEMENT_PART", "0.15"),
        (1398, 1405, "OTHER_REPLACEMENT_PART", "0.20"),
        (1397, 1405, "OTHER_REPLACEMENT_PART", "0.25"),
        (1395, 1405, "OTHER_REPLACEMENT_PART", "0.25"),
        (1380, 1405, "OTHER_REPLACEMENT_PART", "0.25"),  # capped
        (1380, 1405, "GLASS", "0"),
        (1380, 1405, "LAMP_GLASS", "0"),
        (None, 1405, "OTHER_REPLACEMENT_PART", "0"),
    ],
)
def test_replacement_part_depreciation_rate(production_year, claim_year, category, expected):
    assert operators.replacement_part_depreciation_rate(production_year, claim_year, category) == Decimal(expected)


def test_depreciation_before_the_fifth_production_year_is_zero():
    for production_year in (1405, 1404, 1403, 1402):
        assert operators.replacement_part_depreciation_rate(
            production_year, 1405, "OTHER_REPLACEMENT_PART"
        ) == D(0)
    assert operators.replacement_part_depreciation_rate(
        1401, 1405, "OTHER_REPLACEMENT_PART"
    ) == D("0.05")


def test_depreciation_maximum_is_25_percent():
    for production_year in (1395, 1390, 1380, 1350):
        assert operators.replacement_part_depreciation_rate(
            production_year, 1405, "OTHER_REPLACEMENT_PART"
        ) <= D("0.25")


# --------------------------------------------------------- special part cap


def test_battery_and_tire_cap_is_half_of_new_price():
    assert operators.special_part_cap("BATTERY", D(40), D(40)) == D(20)
    assert operators.special_part_cap("TIRE", D(100), D(100)) == D(50)
    assert operators.special_part_cap("TIRE", D(20), D(100)) == D(20)  # already below the cap
    assert operators.special_part_cap("OTHER_REPLACEMENT_PART", D(100), None) == D(100)


def test_special_part_cap_requires_a_new_price():
    with pytest.raises(operators.OperatorError):
        operators.special_part_cap("BATTERY", D(40), None)


# --------------------------------------------------------------- franchise


def test_absolute_franchise():
    assert operators.franchise_amount("ABSOLUTE", absolute=D(10)) == D(10)


def test_percent_franchise_with_and_without_minimum():
    assert operators.franchise_amount("PERCENT", base=D(1000), rate=D("0.10")) == D(100)
    assert (
        operators.franchise_amount("PERCENT_WITH_MINIMUM", base=D(100), rate=D("0.10"), minimum=D(50))
        == D(50)
    )
    assert (
        operators.franchise_amount("PERCENT_WITH_MINIMUM", base=D(1000), rate=D("0.10"), minimum=D(50))
        == D(100)
    )


def test_franchise_without_a_rate_is_an_error_not_a_default():
    with pytest.raises(operators.OperatorError):
        operators.franchise_amount("PERCENT", base=D(1000))


# ------------------------------------------------------- rescue / labour cap


def test_rescue_is_capped_at_twenty_percent():
    assert operators.allowable_rescue_transport(D(60), D(200)) == D(40)
    assert operators.allowable_rescue_transport(D(10), D(200)) == D(10)
    assert operators.allowable_rescue_transport(None, D(200)) == D(0)
    assert operators.allowable_rescue_transport(D(10), None) == D(0)


# ------------------------------------------------------------ salvage / cap


def test_salvage_deduction():
    assert operators.salvage_deduction(D(2000), D(300)) == D(1700)
    assert operators.salvage_deduction(D(2000), None) == D(2000)


def test_liability_cap():
    assert operators.liability_cap(D(300), D(200)) == D(200)
    assert operators.liability_cap(D(300), None) == D(300)
    with pytest.raises(operators.OperatorError):
        operators.liability_cap(None, D(200))


# ------------------------------------------------------- total loss threshold


def test_threshold_is_strictly_greater_than():
    is_total, combined, threshold = operators.is_total_loss(D(1500), D(0), D(2000))
    assert (is_total, combined, threshold) == (False, D(1500), D(1500))

    is_total, _, _ = operators.is_total_loss(D(1500), D(1), D(2000))
    assert is_total is True

    is_total, _, _ = operators.is_total_loss(D(1499), D(0), D(2000))
    assert is_total is False


def test_threshold_needs_both_inputs():
    assert operators.is_total_loss(None, D(0), D(2000)) == (None, None, None)
    assert operators.is_total_loss(D(1000), D(0), None) == (None, None, None)
