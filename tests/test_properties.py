"""Property checks beyond the authored fixture numbers."""

from __future__ import annotations

from decimal import Decimal

from iran_auto_claim.engine import compute
from iran_auto_claim.money import D
from iran_auto_claim.plans import graph_partial_payable, legacy_partial_payable


def _partial(
    gross: int, franchise: int, market: int = 2000, insured: int = 2000
) -> dict:
    return {
        "claim_id": "property",
        "unit": "IRR",
        "classification": {"branch": "PARTIAL_DAMAGE", "domain": "BODY"},
        "event": {"event_date": "1405/06/01"},
        "damage": {"gross": gross, "market": market, "insured": insured},
        "policy": {
            "policy_version": "TEST-v1",
            "franchise": {
                "mode": "ABSOLUTE",
                "absolute_irr": franchise,
                "source": "POLICY",
                "source_reference": "test policy schedule",
                "source_version": "TEST-v1",
            },
        },
    }


def test_missing_franchise_has_no_single_payable(kb):
    payload = _partial(1000, 0)
    del payload["policy"]
    result = compute(payload, kb)
    assert result.payable is None


def test_partial_payable_does_not_fall_when_gross_rises(kb):
    previous: Decimal | None = None
    for gross in (200, 450, 800, 1600):
        result = compute(_partial(gross, 100), kb)
        assert result.payable is not None
        if previous is not None:
            assert result.payable >= previous
        previous = result.payable


def test_a_larger_franchise_does_not_increase_the_payable(kb):
    previous: Decimal | None = None
    for franchise in (0, 40, 100, 250):
        result = compute(_partial(1000, franchise), kb)
        assert result.payable is not None
        if previous is not None:
            assert result.payable <= previous
        previous = result.payable


def test_dropping_franchise_terms_does_not_invent_a_higher_payable(kb):
    complete = compute(_partial(1000, 100), kb)
    assert complete.payable is not None
    missing = dict(_partial(1000, 100))
    del missing["policy"]
    withheld = compute(missing, kb)
    assert withheld.payable is None


def test_total_loss_payable_never_exceeds_the_insured_sum(kb):
    result = compute(
        {
            "claim_id": "cap",
            "unit": "IRR",
            "classification": {"branch": "TOTAL_LOSS"},
            "event": {"event_date": "1405/06/01"},
            "damage": {
                "market": 2000,
                "insured": 1500,
                "repair": 1800,
                "rescue_payable": 900,
            },
            "policy": {
                "policy_version": "TEST-v1",
                "franchise": {
                    "mode": "ABSOLUTE",
                    "absolute_irr": 0,
                    "source": "POLICY",
                    "source_reference": "test policy schedule",
                    "source_version": "TEST-v1",
                },
            },
        },
        kb,
    )
    assert result.payable is not None
    assert result.payable <= D(1500)


def test_graph_sequences_match_legacy_partial_arithmetic(kb):
    after, franchise, ratio, rescue = (
        Decimal(1000),
        Decimal(80),
        Decimal("0.5"),
        Decimal(10),
    )
    branches = (kb.branch("PARTIAL_DAMAGE"), kb.branch("GLASS_ONLY"))
    for branch in branches:
        for scenario in branch["scenarios"]:
            sequence = scenario["sequence"]
            ratio_before = sequence.index("OP_UNDERINSURANCE_RATIO") < sequence.index(
                "OP_FRANCHISE"
            )
            assert graph_partial_payable(after, franchise, ratio, rescue, sequence) == (
                legacy_partial_payable(
                    after, franchise, ratio, rescue, ratio_before=ratio_before
                )
            )
