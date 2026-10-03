"""Executable body plans loaded from the knowledge graph.

The graph supplies the ordered operator ids.  This module owns the bounded
implementation registry that applies those ids; the legacy formulas remain
only as independent parity oracles for tests.
"""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from typing import Any, Callable

FRANCHISE = "OP_FRANCHISE"
RATIO = "OP_UNDERINSURANCE_RATIO"
RESCUE = "OP_RESCUE_CAP"
SALVAGE = "OP_SALVAGE_DEDUCTION"
INSURED_SUM_CAP = "OP_LIABILITY_CAP_INSURED_SUM"


class PlanError(ValueError):
    """The active graph plan is incomplete or cannot be executed safely."""


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
    """Pre-graph formula retained only as a parity oracle."""
    if ratio_before:
        return max(Decimal(0), after_depreciation * ratio - franchise + rescue)
    return max(Decimal(0), (after_depreciation - franchise) * ratio + rescue)


def legacy_total_loss_payable(
    after_salvage: Decimal,
    franchise: Decimal,
    rescue: Decimal,
    insured: Decimal,
) -> Decimal:
    """Pre-graph formula retained only as a parity oracle."""
    return max(Decimal(0), min(after_salvage - franchise + rescue, insured))


def _identity_step(value: Decimal, _: dict[str, Decimal]) -> Decimal:
    return value


def _ratio_step(value: Decimal, operands: dict[str, Decimal]) -> Decimal:
    return value * operands["ratio"]


def _franchise_step(value: Decimal, operands: dict[str, Decimal]) -> Decimal:
    return value - operands["franchise"]


def _rescue_step(value: Decimal, operands: dict[str, Decimal]) -> Decimal:
    return value + operands["rescue"]


def _salvage_step(value: Decimal, operands: dict[str, Decimal]) -> Decimal:
    return value - operands["salvage"]


def _insured_sum_cap_step(value: Decimal, operands: dict[str, Decimal]) -> Decimal:
    return min(value, operands["insured"])


BODY_PLAN_STEPS: dict[str, Callable[[Decimal, dict[str, Decimal]], Decimal]] = {
    "OP_SPECIAL_PART_CAP": _identity_step,
    "OP_DEPRECIATION_REPLACEMENT_PART": _identity_step,
    RATIO: _ratio_step,
    FRANCHISE: _franchise_step,
    RESCUE: _rescue_step,
    SALVAGE: _salvage_step,
    INSURED_SUM_CAP: _insured_sum_cap_step,
}

BODY_PLAN_PATTERNS: dict[str, tuple[tuple[str, ...], ...]] = {
    "PARTIAL_DAMAGE": (
        (
            "OP_SPECIAL_PART_CAP",
            "OP_DEPRECIATION_REPLACEMENT_PART",
            RATIO,
            FRANCHISE,
            RESCUE,
        ),
        (
            "OP_SPECIAL_PART_CAP",
            "OP_DEPRECIATION_REPLACEMENT_PART",
            FRANCHISE,
            RATIO,
            RESCUE,
        ),
    ),
    "GLASS_ONLY": (
        (RATIO, FRANCHISE, RESCUE),
        (FRANCHISE, RATIO, RESCUE),
    ),
    "TOTAL_LOSS": ((SALVAGE, FRANCHISE, RESCUE, INSURED_SUM_CAP),),
    "THEFT": ((FRANCHISE, INSURED_SUM_CAP),),
}


def validate_active_sequence(sequence: list[str], expected: list[str]) -> list[str]:
    """Return a normalized sequence or refuse an incomplete/unknown body plan."""
    normalized = [str(item) for item in sequence]
    expected_ids = [str(item) for item in expected]
    duplicates = sorted({item for item in normalized if normalized.count(item) > 1})
    unknown = sorted(set(normalized) - set(BODY_PLAN_STEPS))
    missing = sorted(set(expected_ids) - set(normalized))
    unexpected = sorted(set(normalized) - set(expected_ids))
    if duplicates or unknown or missing or unexpected or len(normalized) != len(expected_ids):
        details = []
        if duplicates:
            details.append("duplicate operators: " + ", ".join(duplicates))
        if unknown:
            details.append("unknown operators: " + ", ".join(unknown))
        if missing:
            details.append("missing operators: " + ", ".join(missing))
        if unexpected:
            details.append("unexpected operators: " + ", ".join(unexpected))
        if not details:
            details.append("operator count differs from the active branch plan")
        raise PlanError("invalid active body plan; " + "; ".join(details))
    return normalized


def validate_body_sequence(
    branch: str,
    sequence: list[str],
    declared_operators: list[str],
) -> list[str]:
    """Validate membership and supported order for one bounded body plan."""
    patterns = BODY_PLAN_PATTERNS.get(branch)
    if patterns is None:
        raise PlanError(f"no body plan contract is registered for {branch}")
    contract = list(patterns[0])
    validate_active_sequence(declared_operators, contract)
    normalized = validate_active_sequence(sequence, declared_operators)
    if tuple(normalized) not in patterns:
        raise PlanError(
            f"body branch {branch} requests an unsupported operator order: {normalized}"
        )
    return normalized


def plan_identity(branch: str, sequence: list[str], guards: list[str]) -> str:
    """Content-derived identity binding a branch, its sequence, and guard set."""
    payload = json.dumps(
        {"branch": branch, "sequence": sequence, "guards": guards},
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _execute_plan(
    initial: Decimal,
    sequence: list[str],
    operands: dict[str, Decimal],
) -> Decimal:
    value = initial
    for operator_id in sequence:
        step = BODY_PLAN_STEPS.get(operator_id)
        if step is None:
            raise PlanError(f"active body plan has no implementation for {operator_id}")
        value = step(value, operands)
    return max(Decimal(0), value)


def graph_partial_payable(
    after_depreciation: Decimal,
    franchise: Decimal,
    ratio: Decimal,
    rescue: Decimal,
    sequence: list[str],
) -> Decimal:
    """Walk the graph sequence; special-cap/depreciation inputs are pre-applied."""
    return _execute_plan(
        after_depreciation,
        sequence,
        {
            "franchise": franchise,
            "ratio": ratio,
            "rescue": rescue,
            "salvage": Decimal(0),
            "insured": Decimal("Infinity"),
        },
    )


def graph_total_loss_payable(
    settlement_base: Decimal,
    salvage: Decimal,
    franchise: Decimal,
    rescue: Decimal,
    insured: Decimal,
    sequence: list[str],
) -> Decimal:
    """Walk salvage, franchise, rescue, and cap exactly as ordered by the graph."""
    return _execute_plan(
        settlement_base,
        sequence,
        {
            "salvage": salvage,
            "franchise": franchise,
            "rescue": rescue,
            "insured": insured,
            "ratio": Decimal(1),
        },
    )


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
