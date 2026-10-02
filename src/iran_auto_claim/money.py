"""IRR money boundary and explicit presentation conversion.

Persisted cases and the calculation engine use non-negative integer IRR only.
Toman-based units exist solely for explicit import/display conversion.
Rounding occurs once, half-up to the nearest rial, when a display amount enters
the IRR boundary and when a final payable leaves the calculation pipeline.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

IRR_PER_UNIT = {
    "IRR": Decimal(1),
    "toman": Decimal(10),
    "million_toman": Decimal(10_000_000),
    "billion_toman": Decimal(10_000_000_000),
}

UNITS = tuple(IRR_PER_UNIT)


class UnitError(ValueError):
    pass


def D(value: Any) -> Decimal:
    """Coerce to Decimal without ever going through binary float noise."""
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool):
        raise UnitError("booleans are not money")
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, str):
        return Decimal(value.strip())
    raise UnitError(f"cannot interpret {value!r} as money")


def to_irr(amount: Decimal, unit: str) -> Decimal:
    """Explicitly convert a display amount and round half-up to one rial."""
    if unit not in IRR_PER_UNIT:
        raise UnitError(f"unknown unit {unit!r}")
    return round_irr(amount * IRR_PER_UNIT[unit])


def from_irr(amount_irr: Decimal, unit: str) -> Decimal:
    if unit not in IRR_PER_UNIT:
        raise UnitError(f"unknown unit {unit!r}")
    return amount_irr / IRR_PER_UNIT[unit]


def quantize(amount: Decimal, places: int = 2) -> Decimal:
    exp = Decimal(1).scaleb(-places)
    return amount.quantize(exp, rounding=ROUND_HALF_UP)


def round_irr(amount: Decimal) -> Decimal:
    return amount.to_integral_value(rounding=ROUND_HALF_UP)


def fmt(amount: Decimal | None, unit: str = "million_toman") -> str:
    """Format an IRR amount in an explicitly requested presentation unit."""
    if amount is None:
        return "n/a"
    suffix = {
        "IRR": "IRR",
        "toman": "toman",
        "million_toman": "m-toman",
        "billion_toman": "bn-toman",
    }[unit]
    display = from_irr(D(amount), unit)
    places = 0 if unit == "IRR" else 2
    return f"{quantize(display, places):,} {suffix}"
