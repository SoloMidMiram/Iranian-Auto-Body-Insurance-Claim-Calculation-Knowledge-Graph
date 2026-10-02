"""Graph order owns partial scenarios. Legacy arithmetic remains the parity check."""

from __future__ import annotations

from decimal import Decimal

from iran_auto_claim.plans import (
    graph_partial_payable,
    graph_total_loss_payable,
    legacy_partial_payable,
    legacy_total_loss_payable,
)


def test_graph_sequences_match_legacy_partial_arithmetic(kb):
    branch = kb.branch("PARTIAL_DAMAGE")
    after, franchise, ratio, rescue = Decimal(1000), Decimal(100), Decimal("0.5"), Decimal(20)
    for scenario in branch["scenarios"]:
        sequence = scenario["sequence"]
        ratio_before = sequence.index("OP_UNDERINSURANCE_RATIO") < sequence.index("OP_FRANCHISE")
        assert graph_partial_payable(after, franchise, ratio, rescue, sequence) == (
            legacy_partial_payable(after, franchise, ratio, rescue, ratio_before=ratio_before)
        )


def test_swapping_graph_order_changes_the_scenario():
    after, franchise, ratio, rescue = Decimal(1000), Decimal(100), Decimal("0.5"), Decimal(0)
    ratio_first = ["OP_UNDERINSURANCE_RATIO", "OP_FRANCHISE"]
    franchise_first = ["OP_FRANCHISE", "OP_UNDERINSURANCE_RATIO"]
    assert graph_partial_payable(after, franchise, ratio, rescue, ratio_first) == Decimal(400)
    assert graph_partial_payable(after, franchise, ratio, rescue, franchise_first) == Decimal(450)
    assert graph_partial_payable(after, franchise, ratio, rescue, ratio_first) != (
        graph_partial_payable(after, franchise, ratio, rescue, franchise_first)
    )


def test_total_loss_graph_plan_matches_legacy_sum():
    sequence = [
        "OP_SALVAGE_DEDUCTION",
        "OP_FRANCHISE",
        "OP_RESCUE_CAP",
        "OP_LIABILITY_CAP_INSURED_SUM",
    ]
    assert graph_total_loss_payable(
        Decimal(1000), Decimal(100), Decimal(1), Decimal(50), Decimal(2000), sequence
    ) == legacy_total_loss_payable(Decimal(1000), Decimal(100), Decimal(50), Decimal(2000))
