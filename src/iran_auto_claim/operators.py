"""Operator implementations.

These are the eight operator families of the ontology. Each is a pure function
so it can be unit-tested and referenced by id from the registry in
knowledge/operators.json (`implementation` field), which the knowledge loader
verifies resolves to a real callable.

Where the authorities do not settle an operation the function refuses instead of
inventing a value: it raises UncertaintyRequired, which the engine turns into a
scenario set or a refusal.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Sequence

from .money import D

DEPRECIATION_EXEMPT_CATEGORIES = ("GLASS", "LAMP_GLASS")
SPECIAL_CAP_CATEGORIES = ("BATTERY", "TIRE")

BATTERY_TIRE_CAP_RATIO = Decimal("0.50")
RESCUE_CAP_RATIO = Decimal("0.20")
DEPRECIATION_START_YEAR_INDEX = 5
DEPRECIATION_ANNUAL_RATE = Decimal("0.05")
DEPRECIATION_MAX_RATE = Decimal("0.25")


class OperatorError(ValueError):
    """A required input is missing or contradictory."""


class UncertaintyRequired(Exception):
    """The authorities do not settle this operation.

    Attributes:
        uncertainty_id: node_id of the Uncertainty node that must surface.
        status: optional status token; when omitted the engine uses the
            uncertainty_id itself.
        scenarios: candidate outcomes, when they can be expressed.
    """

    def __init__(
        self,
        uncertainty_id: str,
        message: str,
        status: str | None = None,
        scenarios: Sequence[str] | None = None,
    ) -> None:
        super().__init__(message)
        self.uncertainty_id = uncertainty_id
        self.status = status
        self.scenarios = list(scenarios or [])


def underinsurance_ratio(insured_sum: Decimal | None, market_value: Decimal | None) -> Decimal:
    """min(1, insured_sum / actual_market_value_at_event). Capped at 1.

    This is the operator the internet templates call "ماده ۱۰ / Article 10". It
    is a ratio, never a fixed deduction.
    """
    if market_value is None:
        raise OperatorError("market value at event is required to assess underinsurance")
    if insured_sum is None:
        raise OperatorError("insured sum is required to assess underinsurance")
    if market_value <= 0:
        raise OperatorError("market value must be positive")
    if insured_sum >= market_value:
        return Decimal(1)
    if insured_sum <= 0:
        return Decimal(0)
    return insured_sum / market_value


def replacement_part_depreciation_rate(
    production_year: int | None,
    claim_year: int | None,
    part_category: str,
) -> Decimal:
    """Article 19 replacement-part depreciation.

    Glass and lamp glass are expressly exempt. Every other replaced part accrues
    5% per production year beginning with the fifth production year, capped at
    25%. Date completeness is enforced at the case/schema boundary. This
    operator remains total for direct unit use, but settlement code must never
    treat a missing-date zero as evidence that no depreciation applies.
    """
    if part_category in DEPRECIATION_EXEMPT_CATEGORIES:
        return Decimal(0)
    if production_year is None or claim_year is None:
        return Decimal(0)
    year_index = claim_year - production_year + 1
    if year_index < DEPRECIATION_START_YEAR_INDEX:
        return Decimal(0)
    rate = DEPRECIATION_ANNUAL_RATE * (year_index - 4)
    return min(DEPRECIATION_MAX_RATE, rate)


def depreciation_amount(depreciable_base: Decimal, rate: Decimal) -> Decimal:
    if depreciable_base < 0:
        raise OperatorError("depreciable base cannot be negative")
    if rate < 0:
        raise OperatorError("depreciation rate cannot be negative")
    return depreciable_base * rate


def special_part_cap(
    part_category: str,
    assessed_loss: Decimal,
    new_price: Decimal | None,
) -> Decimal:
    """Article 3: battery and tire damage is covered up to 50% of new price."""
    if part_category not in SPECIAL_CAP_CATEGORIES:
        return assessed_loss
    if new_price is None:
        raise OperatorError(
            f"new price is required to apply the 50% cap to {part_category}"
        )
    return min(assessed_loss, BATTERY_TIRE_CAP_RATIO * new_price)


def eligible_part_loss(
    part: dict[str, Any],
    production_year: int | None,
    claim_year: int | None,
    config: dict[str, Any] | None = None,
) -> dict[str, Decimal]:
    """Apply the special-part cap and depreciation to one replacement part.

    The Regulation 53 text does not state whether the 50%-of-new-price ceiling
    and the Article 19 aging schedule stack for an older vehicle, nor in which
    order. When both could apply and the caller has not resolved the
    interaction, this function refuses.
    """
    cfg = config or {}
    category = part["category"]
    assessed = D(part["assessed_loss"])

    capped = special_part_cap(category, assessed, part.get("new_price"))
    requires_replacement = bool(
        part.get("requires_replacement", category != "REPAIR_ONLY")
    )

    override = part.get("depreciation_rate")
    if not requires_replacement:
        rate = Decimal(0)
    else:
        rate = (
            D(override)
            if override is not None
            else replacement_part_depreciation_rate(production_year, claim_year, category)
        )

    if category in SPECIAL_CAP_CATEGORIES and rate > 0:
        interaction = cfg.get("battery_tire_depreciation_interaction", "UNRESOLVED")
        if interaction == "UNRESOLVED":
            raise UncertaintyRequired(
                "U04_BATTERY_TIRE_CAP_VS_DEPRECIATION",
                (
                    f"{category} is old enough to depreciate and is also subject to the "
                    "50%-of-new-price cap; the interaction order is not stated in the text"
                ),
                status="BATTERY_TIRE_INTERACTION_UNRESOLVED",
                scenarios=["CAP_THEN_DEPRECIATE", "DEPRECIATE_THEN_CAP", "CAP_ONLY"],
            )
        if interaction == "CAP_THEN_DEPRECIATE":
            scheduled_depreciation = depreciation_amount(capped, rate)
            after_depreciation = capped - scheduled_depreciation
        elif interaction == "DEPRECIATE_THEN_CAP":
            scheduled_depreciation = depreciation_amount(assessed, rate)
            after_depreciation = special_part_cap(
                category, assessed - scheduled_depreciation, part.get("new_price")
            )
        elif interaction == "CAP_ONLY":
            rate = Decimal(0)
            scheduled_depreciation = Decimal(0)
            after_depreciation = capped
        else:
            raise OperatorError(
                f"unknown battery/tire depreciation interaction {interaction!r}"
            )
    else:
        scheduled_depreciation = depreciation_amount(capped, rate)
        after_depreciation = capped - scheduled_depreciation

    # Report the effective deduction from the already capped eligible loss.
    # In DEPRECIATE_THEN_CAP the cap may absorb some or all of the scheduled
    # depreciation; subtracting the scheduled amount again would apply it twice.
    effective_depreciation = capped - after_depreciation
    return {
        "capped_loss": capped,
        "loss_after_depreciation": after_depreciation,
        "depreciation_rate": rate,
        "scheduled_depreciation_amount": scheduled_depreciation,
        "depreciation_amount": effective_depreciation,
    }


def franchise_amount(
    mode: str,
    base: Decimal | None = None,
    rate: Decimal | None = None,
    absolute: Decimal | None = None,
    minimum: Decimal | None = None,
) -> Decimal:
    """Franchise is the insured's share whose amount is specified in the policy.

    No universal statutory rate exists, so a percent-mode franchise must carry a
    rate; the caller (engine) is responsible for having a policy source, which
    guardrail G_NO_HARDCODED_FRANCHISE_RATE enforces.
    """
    mode = (mode or "ABSOLUTE").upper()
    if mode == "ABSOLUTE":
        if absolute is None:
            raise OperatorError("absolute franchise requires an amount")
        return absolute
    if mode in ("PERCENT", "PERCENT_WITH_MINIMUM"):
        if rate is None:
            raise OperatorError("percent franchise requires a rate")
        if base is None:
            raise OperatorError("percent franchise requires a calculation base")
        amount = base * rate
        if mode == "PERCENT_WITH_MINIMUM" and minimum is not None:
            amount = max(amount, minimum)
        return amount
    raise OperatorError(f"unknown franchise mode {mode!r}")


def allowable_rescue_transport(actual_cost: Decimal | None, cap_base: Decimal | None) -> Decimal:
    """min(actual, 20% of the statutory cap base).

    The regulation fixes the ceiling at 20% of total damage but does not define
    the denominator when depreciation or underinsurance is also in play, so the
    base is supplied by the caller from configuration (U05).
    """
    if actual_cost is None or actual_cost <= 0:
        return Decimal(0)
    if cap_base is None or cap_base <= 0:
        return Decimal(0)
    return min(actual_cost, RESCUE_CAP_RATIO * cap_base)


def salvage_deduction(settlement_base: Decimal, salvage_value: Decimal | None) -> Decimal:
    """Deduct probable salvage. Only the salvage-retained route may call this.

    Central Insurance circular 1400/401/146850 then places the total-loss
    franchise after this deduction.
    """
    if salvage_value is None:
        return settlement_base
    return settlement_base - salvage_value


def liability_cap(assessed_liability: Decimal | None, cap: Decimal | None) -> Decimal:
    if assessed_liability is None:
        raise OperatorError("assessed liability is required")
    if cap is None:
        return assessed_liability
    return min(assessed_liability, cap)


def is_total_loss(
    repair_and_replacement: Decimal | None,
    rescue_for_test: Decimal | None,
    market_value: Decimal | None,
) -> tuple[bool | None, Decimal | None, Decimal | None]:
    """Article 19 threshold test: strictly more than 75% of market value.

    Returns (is_total, combined, threshold). Equality is not a total loss.
    """
    if market_value is None or repair_and_replacement is None:
        return None, None, None
    combined = repair_and_replacement + (rescue_for_test or Decimal(0))
    threshold = market_value * Decimal("0.75")
    return combined > threshold, combined, threshold
