"""Small dependency-free oracle used by the curated calculation mutation gate."""

from __future__ import annotations

from decimal import Decimal

from iran_auto_claim.engine import CalcResult, _enforce_guard_plan, compute
from iran_auto_claim.knowledge import Knowledge
from iran_auto_claim.operators import (
    allowable_rescue_transport,
    is_total_loss,
    underinsurance_ratio,
)
from iran_auto_claim.plans import (
    PlanError,
    graph_partial_payable,
    graph_total_loss_payable,
    validate_active_sequence,
)


def main() -> int:
    ratio_first = [
        "OP_SPECIAL_PART_CAP",
        "OP_DEPRECIATION_REPLACEMENT_PART",
        "OP_UNDERINSURANCE_RATIO",
        "OP_FRANCHISE",
        "OP_RESCUE_CAP",
    ]
    franchise_first = [
        "OP_SPECIAL_PART_CAP",
        "OP_DEPRECIATION_REPLACEMENT_PART",
        "OP_FRANCHISE",
        "OP_UNDERINSURANCE_RATIO",
        "OP_RESCUE_CAP",
    ]
    assert graph_partial_payable(
        Decimal(1000), Decimal(100), Decimal("0.5"), Decimal(20), ratio_first
    ) == Decimal(420)
    assert graph_partial_payable(
        Decimal(1000), Decimal(100), Decimal("0.5"), Decimal(20), franchise_first
    ) == Decimal(470)

    total_sequence = [
        "OP_SALVAGE_DEDUCTION",
        "OP_FRANCHISE",
        "OP_RESCUE_CAP",
        "OP_LIABILITY_CAP_INSURED_SUM",
    ]
    assert graph_total_loss_payable(
        Decimal(1200),
        Decimal(200),
        Decimal(100),
        Decimal(50),
        Decimal(900),
        total_sequence,
    ) == Decimal(900)
    assert graph_total_loss_payable(
        Decimal(1200),
        Decimal(200),
        Decimal(100),
        Decimal(50),
        Decimal(2000),
        total_sequence,
    ) == Decimal(950)
    assert graph_total_loss_payable(
        Decimal(50),
        Decimal(0),
        Decimal(100),
        Decimal(0),
        Decimal(1000),
        total_sequence,
    ) == Decimal(0)

    try:
        validate_active_sequence(
            ["OP_UNDERINSURANCE_RATIO", "OP_RESCUE_CAP"],
            ["OP_UNDERINSURANCE_RATIO", "OP_FRANCHISE", "OP_RESCUE_CAP"],
        )
    except PlanError:
        pass
    else:
        raise AssertionError("a missing active operator was accepted")

    assert allowable_rescue_transport(Decimal(500), Decimal(1000)) == Decimal(200)
    assert underinsurance_ratio(Decimal(2500), Decimal(2000)) == Decimal(1)
    equal, _, _ = is_total_loss(Decimal(750), Decimal(0), Decimal(1000))
    above, _, _ = is_total_loss(Decimal(751), Decimal(0), Decimal(1000))
    assert equal is False
    assert above is True

    result = CalcResult(branch="PARTIAL_DAMAGE", payable=Decimal(100))
    result.require_guard("G_NO_HARDCODED_FRANCHISE_RATE")
    _enforce_guard_plan(result)
    assert result.payable is None
    assert result.status == "GUARD_PLAN_INCOMPLETE"

    missing_franchise = compute(
        {
            "claim_id": "mutation-probe",
            "unit": "IRR",
            "classification": {"branch": "PARTIAL_DAMAGE", "domain": "BODY"},
            "event": {"event_date": "1405/06/01"},
            "damage": {"gross": 1000},
        },
        Knowledge.load(),
    )
    assert missing_franchise.payable is None
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
