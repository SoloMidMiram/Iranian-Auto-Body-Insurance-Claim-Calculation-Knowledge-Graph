"""Body operator order comes from the graph.

The legacy formulas stay here so a graph sequence can be compared with the
previous arithmetic before a caller treats the graph as the only order.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

FRANCHISE = "OP_FRANCHISE"
RATIO = "OP_UNDERINSURANCE_RATIO"


def ratio_before_franchise(sequence: list[str]) -> bool:
    return sequence.index(RATIO) < sequence.index(FRANCHISE)


def legacy_partial_payable(
    after_depreciation: Decimal,
    franchise: Decimal,
    ratio: Decimal,
    rescue: Decimal,
    *,
    ratio_before: bool,
) -> Decimal:
    if ratio_before:
        return max(Decimal(0), after_depreciation * ratio - franchise + rescue)
    return max(Decimal(0), (after_depreciation - franchise) * ratio + rescue)


def graph_partial_payable(
    after_depreciation: Decimal,
    franchise: Decimal,
    ratio: Decimal,
    rescue: Decimal,
    sequence: list[str],
) -> Decimal:
    return legacy_partial_payable(
        after_depreciation,
        franchise,
        ratio,
        rescue,
        ratio_before=ratio_before_franchise(sequence),
    )


def legacy_total_loss_payable(
    after_salvage: Decimal,
    franchise: Decimal,
    rescue: Decimal,
    insured: Decimal,
) -> Decimal:
    return max(Decimal(0), min(after_salvage - franchise + rescue, insured))


def graph_total_loss_payable(
    after_salvage: Decimal,
    franchise: Decimal,
    ratio_unused: Decimal,
    rescue: Decimal,
    insured: Decimal,
    sequence: list[str],
) -> Decimal:
    """Salvage, franchise, rescue, and the insured-sum cap commute for this sum."""
    del ratio_unused
    if "OP_SALVAGE_DEDUCTION" not in sequence or "OP_LIABILITY_CAP_INSURED_SUM" not in sequence:
        raise ValueError("total-loss plan is missing salvage or the insured-sum cap")
    return legacy_total_loss_payable(after_salvage, franchise, rescue, insured)


def named_sequence(branch: dict[str, Any], name: str) -> list[str] | None:
    for scenario in branch.get("scenarios") or []:
        if scenario.get("name") == name and scenario.get("sequence"):
            return [str(item) for item in scenario["sequence"]]
    return None


def sequences_with_ratio(branch: dict[str, Any]) -> list[list[str]]:
    found: list[list[str]] = []
    for scenario in branch.get("scenarios") or []:
        sequence = [str(item) for item in scenario.get("sequence") or []]
        if RATIO in sequence and FRANCHISE in sequence:
            found.append(sequence)
    return found
