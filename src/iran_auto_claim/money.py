"""Money handling.

Production callers should supply integer IRR and set unit=IRR. Assessment
fixtures use million tomans for readability, so the engine is deliberately
unit-agnostic: it computes in the case's declared unit and only converts when it
must intersect a value whose unit is fixed (the annual parameters, which are
stored in IRR).

1 toman = 10 IRR.
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
    if unit not in IRR_PER_UNIT:
        raise UnitError(f"unknown unit {unit!r}")
    return amount * IRR_PER_UNIT[unit]


def from_irr(amount_irr: Decimal, unit: str) -> Decimal:
    if unit not in IRR_PER_UNIT:
        raise UnitError(f"unknown unit {unit!r}")
    return amount_irr / IRR_PER_UNIT[unit]


def quantize(amount: Decimal, places: int = 2) -> Decimal:
    exp = Decimal(1).scaleb(-places)
    return amount.quantize(exp, rounding=ROUND_HALF_UP)


def fmt(amount: Decimal | None, unit: str = "million_toman") -> str:
    if amount is None:
        return "n/a"
    suffix = {
        "IRR": "IRR",
        "toman": "toman",
        "million_toman": "m-toman",
        "billion_toman": "bn-toman",
    }[unit]
    return f"{quantize(amount, 2):,} {suffix}"
