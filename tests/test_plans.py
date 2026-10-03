"""Graph order owns partial scenarios. Legacy arithmetic remains the parity check."""

from __future__ import annotations

import copy
from decimal import Decimal

import pytest

from iran_auto_claim.engine import compute
from iran_auto_claim.fixtures import evaluate_fixture, load_fixtures
from iran_auto_claim.plans import (
    PlanError,
    graph_partial_payable,
    graph_total_loss_payable,
    legacy_partial_payable,
    legacy_total_loss_payable,
    plan_identity,
    validate_active_sequence,
    validate_body_sequence,
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
        Decimal(1200), Decimal(200), Decimal(100), Decimal(50), Decimal(2000), sequence
    ) == legacy_total_loss_payable(Decimal(1000), Decimal(100), Decimal(50), Decimal(2000))


def test_plan_identity_binds_sequence_and_guard_set():
    sequence = ["OP_UNDERINSURANCE_RATIO", "OP_FRANCHISE", "OP_RESCUE_CAP"]
    guards = ["G_NO_HARDCODED_FRANCHISE_RATE"]
    identity = plan_identity("GLASS_ONLY", sequence, guards)
    assert identity.startswith("sha256:")
    assert identity != plan_identity("GLASS_ONLY", list(reversed(sequence)), guards)
    assert identity != plan_identity("GLASS_ONLY", sequence, guards + ["G_RESCUE_CAP_CEILING"])


def test_body_fixture_plans_record_identity_and_complete_required_guards(kb):
    for fixture in load_fixtures():
        result, problems = evaluate_fixture(fixture, kb)
        assert not problems, fixture["id"]
        if "execution_plan" not in result.fields:
            continue
        assert result.fields.get("execution_plan_id") or result.fields.get("execution_plan_ids")
        assert set(result.fields["execution_plan_guards"]) <= set(result.required_guards)
        assert set(result.required_guards) <= set(result.guards_executed)


@pytest.mark.parametrize(
    "sequence",
    [
        ["OP_FRANCHISE", "OP_RESCUE_CAP"],
        ["OP_FRANCHISE", "OP_UNKNOWN", "OP_RESCUE_CAP"],
        ["OP_FRANCHISE", "OP_FRANCHISE", "OP_RESCUE_CAP"],
    ],
)
def test_active_plan_refuses_missing_unknown_or_duplicate_operators(sequence):
    expected = ["OP_UNDERINSURANCE_RATIO", "OP_FRANCHISE", "OP_RESCUE_CAP"]
    with pytest.raises(PlanError):
        validate_active_sequence(sequence, expected)


def test_body_contract_refuses_a_missing_declared_operator():
    declared = ["OP_SALVAGE_DEDUCTION", "OP_FRANCHISE", "OP_LIABILITY_CAP_INSURED_SUM"]
    with pytest.raises(PlanError):
        validate_body_sequence("TOTAL_LOSS", declared, declared)


@pytest.mark.parametrize("mutation", ["missing", "unknown"])
def test_compute_refuses_a_broken_active_body_sequence(kb, mutation):
    changed = copy.deepcopy(kb)
    sequence = changed.branches["PARTIAL_DAMAGE"]["scenarios"][0]["sequence"]
    if mutation == "missing":
        sequence.remove("OP_FRANCHISE")
    else:
        sequence[0] = "OP_UNKNOWN"
    result = compute(
        {
            "claim_id": "bad-plan",
            "unit": "IRR",
            "classification": {"branch": "PARTIAL_DAMAGE", "domain": "BODY"},
            "event": {"event_date": "1405/06/01"},
            "damage": {"gross": 1000, "market": 2000, "insured": 1000},
            "policy": {
                "policy_version": "TEST-v1",
                "franchise": {
                    "mode": "ABSOLUTE",
                    "absolute_irr": 100,
                    "source": "POLICY",
                    "source_reference": "test policy schedule",
                    "source_version": "TEST-v1",
                },
            },
            "calculation_config": {
                "article10_partial_order": "AFTER_DEPRECIATION_BEFORE_FRANCHISE"
            },
        },
        changed,
    )
    assert result.payable is None
    assert result.status == "EXECUTION_PLAN_INVALID"


# ------------------------------------------------------------------ glass order


def _glass_case(config: dict | None) -> dict:
    """Endorsed, underinsured glass with sourced franchise terms (ratio 0.5)."""
    payload = {
        "claim_id": "glass-resolved-order",
        "unit": "IRR",
        "classification": {"branch": "GLASS_ONLY"},
        "event": {"event_date": "1405/06/01"},
        "damage": {
            "glass_endorsement": True,
            "gross": 1000,
            "market": 2000,
            "insured": 1000,
        },
        "policy": {
            "policy_version": "TEST-v1",
            "franchise": {
                "mode": "ABSOLUTE",
                "absolute_irr": 100,
                "source": "POLICY",
                "source_reference": "test policy schedule",
                "source_version": "TEST-v1",
            },
        },
    }
    if config is not None:
        payload["calculation_config"] = config
    return payload


@pytest.mark.parametrize("order", [None, "UNRESOLVED", "INSURER_SPECIFIC"])
def test_endorsement_flag_alone_never_selects_one_glass_payable(kb, order):
    """Flag true with a missing or unresolved order keeps the scenario set."""
    config: dict[str, object] = {"glass_article10_order_resolved_by_endorsement": True}
    if order is not None:
        config["article10_partial_order"] = order
    result = compute(_glass_case(config), kb)
    assert result.payable is None
    assert result.status == "ENDORSEMENT_AND_ORDER_REQUIRED"
    assert result.payable_scenarios == [Decimal(400), Decimal(450)]


@pytest.mark.parametrize(
    ("order", "payable"),
    [
        ("AFTER_DEPRECIATION_BEFORE_FRANCHISE", 400),
        ("AFTER_DEPRECIATION_AND_FRANCHISE", 450),
    ],
)
def test_endorsed_glass_uses_the_explicitly_resolved_order(kb, order, payable):
    """Flag true plus one of the two supported orders selects that single outcome."""
    config = {
        "article10_partial_order": order,
        "glass_article10_order_resolved_by_endorsement": True,
    }
    result = compute(_glass_case(config), kb)
    assert result.payable == Decimal(payable)
    assert result.fields["order_used"] == order
    assert result.payable_scenarios == []
