"""Each guard is executed on a path, with a firing case and a non-firing case."""

from __future__ import annotations

import copy

import pytest
from admission_shim import compute as admitted_compute

from iran_auto_claim.engine import CalcResult, _enforce_guard_plan
from iran_auto_claim.money import D


ALL_GUARDS = [
    "G_NO_DOUBLE_UNDERINSURANCE_IN_TOTAL_LOSS",
    "G_SALVAGE_XOR_TITLE_TRANSFER",
    "G_RESCUE_CAP_CEILING",
    "G_INSURED_SUM_CEILING",
    "G_DUAL_LIABILITY_CAP",
    "G_ARTICLE8_NO_WHOLE_CAR_RATIO",
    "G_NO_HARDCODED_FRANCHISE_RATE",
    "G_NO_UNIVERSAL_GLASS_FRANCHISE",
    "G_GLASS_ARTICLE10_NOT_AUTO_EXEMPT",
    "G_NO_MANDATORY_FRANCHISE_WITHOUT_DISCLOSURE",
    "G_NO_GUESSED_ENDORSEMENT_TERMS",
    "G_NO_ASSUMED_CAUSATION",
    "G_UNCERTAINTY_MUST_SURFACE",
]


def _policy(
    franchise: int = 100, mode: str = "ABSOLUTE", source: str = "POLICY"
) -> dict:
    spec = {
        "mode": mode,
        "source": source,
        "source_reference": "test policy schedule",
        "source_version": "TEST-v1",
    }
    if mode == "ABSOLUTE":
        spec["absolute_irr"] = franchise
    else:
        spec["rate"] = "0.10"
        spec["calculation_base"] = "AFTER_DEPRECIATION"
    return {"policy_version": "TEST-v1", "franchise": spec}


def compute(payload, kb):
    """Make the guard-focused synthetic assumptions explicit."""
    payload = copy.deepcopy(payload)
    branch = (payload.get("classification") or {}).get("branch")
    damage = payload.setdefault("damage", {})
    if branch == "PARTIAL_DAMAGE":
        if not any(key in damage for key in ("market", "insured")):
            damage["market"] = 10**12
            damage["insured"] = 10**12
        if not any(
            key in damage
            for key in ("depreciation", "depreciable_parts", "parts", "replacement_parts")
        ):
            damage["depreciation"] = 0
    if branch == "TOTAL_LOSS" and any(
        key in damage for key in ("salvage", "salvage_value")
    ):
        damage.setdefault("salvage_disposition", "INSURED_RETAINS")
    franchise = ((payload.get("policy") or {}).get("franchise") or {})
    if str(franchise.get("mode") or "").startswith("PERCENT"):
        franchise.setdefault("calculation_base", "AFTER_DEPRECIATION")
    if (damage.get("rescue_payable") or damage.get("actual_rescue")) and branch in (
        "PARTIAL_DAMAGE",
        "TOTAL_LOSS",
    ):
        payload.setdefault("calculation_config", {}).setdefault(
            "rescue_cap_base", "ASSESSED_GROSS"
        )
    return admitted_compute(payload, kb)


@pytest.mark.parametrize("guard_id", ALL_GUARDS, ids=ALL_GUARDS)
def test_each_bypassed_required_guard_fails_the_result(guard_id):
    result = CalcResult(branch="PARTIAL_DAMAGE", payable=D(100))
    result.require_guard(guard_id)
    _enforce_guard_plan(result)
    assert result.payable is None
    assert result.status == "GUARD_PLAN_INCOMPLETE"
    assert result.fields["missing_required_guards"] == [guard_id]


def test_article8_guards_are_not_bound_to_body_plans(kb):
    article8_guards = {
        "G_DUAL_LIABILITY_CAP",
        "G_ARTICLE8_NO_WHOLE_CAR_RATIO",
        "G_NO_MANDATORY_FRANCHISE_WITHOUT_DISCLOSURE",
    }
    for branch_name in ("PARTIAL_DAMAGE", "TOTAL_LOSS", "GLASS_ONLY", "THEFT"):
        assert article8_guards.isdisjoint(kb.branch(branch_name).get("guardrails") or [])


def test_total_loss_guards_fire_and_also_run_when_they_do_not_breach(kb):
    underinsured = compute(
        {
            "claim_id": "tl-under",
            "unit": "IRR",
            "classification": {"branch": "TOTAL_LOSS"},
            "event": {"event_date": "1405/06/01"},
            "damage": {"market": 2000, "insured": 1000, "repair": 1600},
            "policy": _policy(0),
        },
        kb,
    )
    assert "G_NO_DOUBLE_UNDERINSURANCE_IN_TOTAL_LOSS" in underinsured.guards_executed
    assert "DO_NOT_APPLY_RATIO_TWICE" in underinsured.labels

    matched = compute(
        {
            "claim_id": "tl-match",
            "unit": "IRR",
            "classification": {"branch": "TOTAL_LOSS"},
            "event": {"event_date": "1405/06/01"},
            "damage": {"market": 2000, "insured": 2000, "repair": 1600},
            "policy": _policy(100),
        },
        kb,
    )
    assert "G_NO_DOUBLE_UNDERINSURANCE_IN_TOTAL_LOSS" in matched.guards_executed
    assert "DO_NOT_APPLY_RATIO_TWICE" not in matched.labels
    assert "G_SALVAGE_XOR_TITLE_TRANSFER" in matched.guards_executed
    assert "G_INSURED_SUM_CEILING" in matched.guards_executed
    assert "INSURED_SUM_CEILING_APPLIED" not in matched.labels

    capped = compute(
        {
            "claim_id": "tl-cap",
            "unit": "IRR",
            "classification": {"branch": "TOTAL_LOSS"},
            "event": {"event_date": "1405/06/01"},
            "damage": {
                "market": 1000,
                "insured": 1000,
                "repair": 800,
                "actual_rescue": 500,
            },
            "policy": _policy(0),
        },
        kb,
    )
    assert "G_INSURED_SUM_CEILING" in capped.guards_executed
    assert "INSURED_SUM_CEILING_APPLIED" in capped.labels
    assert capped.payable == D(1000)

    transferred = compute(
        {
            "claim_id": "tl-title",
            "unit": "IRR",
            "classification": {"branch": "TOTAL_LOSS"},
            "event": {"event_date": "1405/06/01"},
            "damage": {
                "market": 2000,
                "insured": 2000,
                "repair": 1600,
                "salvage_value": 300,
                "salvage_disposition": "INSURER_TAKES_TITLE",
            },
            "policy": _policy(100),
        },
        kb,
    )
    assert "G_SALVAGE_XOR_TITLE_TRANSFER" in transferred.guards_executed
    assert "DO_NOT_DEDUCT_SALVAGE_AND_TRANSFER_IT" in transferred.labels


def test_rescue_cap_runs_when_the_claim_is_under_and_over_the_ceiling(kb):
    under = compute(
        {
            "claim_id": "rescue-under",
            "unit": "IRR",
            "classification": {"branch": "PARTIAL_DAMAGE"},
            "event": {"event_date": "1405/06/01"},
            "damage": {"gross": 1000, "actual_rescue": 10},
            "policy": _policy(0),
        },
        kb,
    )
    assert "G_RESCUE_CAP_CEILING" in under.guards_executed
    assert "RESCUE_CAPPED" not in under.labels

    over = compute(
        {
            "claim_id": "rescue-over",
            "unit": "IRR",
            "classification": {"branch": "PARTIAL_DAMAGE"},
            "event": {"event_date": "1405/06/01"},
            "damage": {"gross": 1000, "actual_rescue": 900},
            "policy": _policy(0),
        },
        kb,
    )
    assert "G_RESCUE_CAP_CEILING" in over.guards_executed
    assert "RESCUE_CAPPED" in over.labels
    assert over.payable <= D(1000) + D(200)


def test_franchise_source_guard_rejects_an_unsourced_rate_and_accepts_absolute(kb):
    refused = compute(
        {
            "claim_id": "rate",
            "unit": "IRR",
            "classification": {"branch": "PARTIAL_DAMAGE"},
            "event": {"event_date": "1405/06/01"},
            "damage": {"gross": 1000},
            "policy": {
                "policy_version": "TEST-v1",
                "franchise": {"mode": "PERCENT", "rate": 0.1, "source": "UNKNOWN"},
            },
        },
        kb,
    )
    assert "G_NO_HARDCODED_FRANCHISE_RATE" in refused.guards_executed
    assert refused.status == "GUARD_VIOLATION_UNSOURCED_FRANCHISE_RATE"

    accepted = compute(
        {
            "claim_id": "absolute",
            "unit": "IRR",
            "classification": {"branch": "PARTIAL_DAMAGE"},
            "event": {"event_date": "1405/06/01"},
            "damage": {"gross": 1000},
            "policy": _policy(10),
        },
        kb,
    )
    assert "G_NO_HARDCODED_FRANCHISE_RATE" in accepted.guards_executed
    assert accepted.payable == D(990)


def test_glass_guards_reject_a_universal_rate_and_keep_a_sourced_franchise(kb):
    refused = compute(
        {
            "claim_id": "glass-rate",
            "unit": "IRR",
            "classification": {"branch": "GLASS_ONLY"},
            "event": {"event_date": "1405/06/01"},
            "damage": {
                "glass_endorsement": True,
                "gross": 100,
                "glass_franchise_rate": 0.2,
                "market": 2500,
                "insured": 2500,
            },
            "policy": _policy(0),
        },
        kb,
    )
    assert "G_NO_UNIVERSAL_GLASS_FRANCHISE" in refused.guards_executed
    assert refused.status == "GUARD_VIOLATION_UNIVERSAL_GLASS_FRANCHISE"

    allowed = compute(
        {
            "claim_id": "glass-ok",
            "unit": "IRR",
            "classification": {"branch": "GLASS_ONLY"},
            "event": {"event_date": "1405/06/01"},
            "damage": {
                "glass_endorsement": True,
                "gross": 100,
                "market": 2500,
                "insured": 2500,
            },
            "policy": _policy(10),
        },
        kb,
    )
    assert "G_NO_UNIVERSAL_GLASS_FRANCHISE" in allowed.guards_executed
    assert allowed.status != "GUARD_VIOLATION_UNIVERSAL_GLASS_FRANCHISE"
    assert allowed.payable == D(90)


def test_glass_underinsurance_is_not_silently_exempted(kb):
    unresolved = compute(
        {
            "claim_id": "glass-order",
            "unit": "IRR",
            "classification": {"branch": "GLASS_ONLY"},
            "event": {"event_date": "1405/06/01"},
            "damage": {
                "glass_endorsement": True,
                "gross": 100,
                "market": 2000,
                "insured": 1000,
            },
            "policy": _policy(10),
        },
        kb,
    )
    assert "G_GLASS_ARTICLE10_NOT_AUTO_EXEMPT" in unresolved.guards_executed
    assert unresolved.payable is None

    resolved = compute(
        {
            "claim_id": "glass-resolved",
            "unit": "IRR",
            "classification": {"branch": "GLASS_ONLY"},
            "event": {"event_date": "1405/06/01"},
            "damage": {
                "glass_endorsement": True,
                "gross": 100,
                "market": 2000,
                "insured": 1000,
            },
            "policy": _policy(10),
            "calculation_config": {
                "article10_partial_order": "AFTER_DEPRECIATION_BEFORE_FRANCHISE",
                "glass_article10_order_resolved_by_endorsement": True,
            },
        },
        kb,
    )
    assert "G_GLASS_ARTICLE10_NOT_AUTO_EXEMPT" in resolved.guards_executed
    assert resolved.payable is not None
    assert "GLASS_UNDERINSURANCE_UNRESOLVED" not in resolved.labels


def test_endorsement_terms_are_not_guessed_and_a_plain_claim_is_not_excluded(kb):
    endorsed = compute(
        {
            "claim_id": "flood-endorsed",
            "unit": "IRR",
            "classification": {"branch": "PARTIAL_DAMAGE"},
            "event": {"event_date": "1405/06/01", "peril": "FLOOD"},
            "damage": {"gross": 1000, "endorsement": True},
            "policy": _policy(10),
        },
        kb,
    )
    assert "G_NO_GUESSED_ENDORSEMENT_TERMS" in endorsed.guards_executed
    assert endorsed.status == "ENDORSEMENT_TERMS_REQUIRED"

    plain = compute(
        {
            "claim_id": "plain",
            "unit": "IRR",
            "classification": {"branch": "PARTIAL_DAMAGE"},
            "event": {"event_date": "1405/06/01", "peril": "COLLISION"},
            "damage": {"gross": 1000},
            "policy": _policy(10),
        },
        kb,
    )
    assert plain.payable == D(990)
    assert "G_NO_GUESSED_ENDORSEMENT_TERMS" not in plain.guards_executed


def test_causation_token_excludes_and_narrative_text_does_not(kb):
    coded = compute(
        {
            "claim_id": "cause",
            "unit": "IRR",
            "classification": {"branch": "PARTIAL_DAMAGE"},
            "event": {
                "event_date": "1405/06/01",
                "cause": "DRIVER_INTOXICATION_CAUSALLY_CONFIRMED",
                "intoxication_causally_confirmed": True,
            },
            "damage": {"gross": 1000},
            "policy": _policy(10),
        },
        kb,
    )
    assert "G_NO_ASSUMED_CAUSATION" in coded.guards_executed
    assert coded.payable == D(0)

    narrative = compute(
        {
            "claim_id": "narrative",
            "unit": "IRR",
            "classification": {"branch": "PARTIAL_DAMAGE"},
            "event": {
                "event_date": "1405/06/01",
                "cause": "driver mentioned alcohol in a statement",
            },
            "damage": {"gross": 1000},
            "policy": _policy(10),
        },
        kb,
    )
    assert narrative.payable == D(990)
    assert "G_NO_ASSUMED_CAUSATION" not in narrative.guards_executed


def test_uncertainty_guard_blocks_a_single_payable_and_allows_a_settled_claim(kb):
    unresolved = compute(
        {
            "claim_id": "order",
            "unit": "IRR",
            "classification": {"branch": "PARTIAL_DAMAGE"},
            "event": {"event_date": "1405/06/01"},
            "damage": {"gross": 1000, "market": 2000, "insured": 1000},
            "policy": _policy(10),
        },
        kb,
    )
    assert "G_UNCERTAINTY_MUST_SURFACE" in unresolved.guards_executed
    assert unresolved.payable is None

    settled = compute(
        {
            "claim_id": "settled",
            "unit": "IRR",
            "classification": {"branch": "PARTIAL_DAMAGE"},
            "event": {"event_date": "1405/06/01"},
            "damage": {"gross": 1000, "market": 2000, "insured": 2000},
            "policy": _policy(10),
        },
        kb,
    )
    assert "G_UNCERTAINTY_MUST_SURFACE" in settled.guards_executed
    assert settled.payable == D(990)


def test_article8_caps_run_without_changing_the_refusal_for_a_whole_car_ratio(kb):
    refused = compute(
        {
            "claim_id": "a8-bad",
            "unit": "IRR",
            "classification": {"branch": "ARTICLE_8_NON_CONVENTIONAL"},
            "damage": {
                "vehicle_value": 2500,
                "actual_damage": 300,
                "corresponding_damage": 180,
                "policy_financial_limit": 200,
                "whole_car_ratio": 0.56,
            },
        },
        kb,
    )
    assert "G_ARTICLE8_NO_WHOLE_CAR_RATIO" in refused.guards_executed
    assert refused.payable is None

    capped = compute(
        {
            "claim_id": "a8-cap",
            "unit": "IRR",
            "classification": {"branch": "ARTICLE_8_NON_CONVENTIONAL"},
            "damage": {
                "vehicle_value": 2500,
                "actual_damage": 300,
                "corresponding_damage": 180,
                "policy_financial_limit": 100,
            },
        },
        kb,
    )
    assert "G_DUAL_LIABILITY_CAP" in capped.guards_executed
    assert "G_ARTICLE8_NO_WHOLE_CAR_RATIO" in capped.guards_executed
    assert capped.payable == D(100)

    uncapped = compute(
        {
            "claim_id": "a8-under",
            "unit": "IRR",
            "classification": {"branch": "ARTICLE_8_NON_CONVENTIONAL"},
            "damage": {
                "vehicle_value": 2500,
                "actual_damage": 80,
                "corresponding_damage": 80,
                "policy_financial_limit": 200,
            },
        },
        kb,
    )
    assert "G_DUAL_LIABILITY_CAP" in uncapped.guards_executed
    assert "DUAL_CAP_APPLIED" not in uncapped.labels
    assert uncapped.payable == D(80)


def test_article8_excess_does_not_invent_a_mandatory_franchise(kb):
    hidden = compute(
        {
            "claim_id": "a8-excess",
            "unit": "IRR",
            "classification": {"branch": "ARTICLE_8_DUAL_COVERAGE"},
            "damage": {
                "vehicle_value": 2500,
                "actual_damage": 300,
                "corresponding_damage": 180,
                "policy_financial_limit": 200,
                "has_body_policy": True,
            },
        },
        kb,
    )
    assert "G_NO_MANDATORY_FRANCHISE_WITHOUT_DISCLOSURE" in hidden.guards_executed
    assert hidden.fields["regulatory_mandatory_franchise_on_this_excess"] == D(0)

    disclosed = compute(
        {
            "claim_id": "a8-disclosed",
            "unit": "IRR",
            "classification": {"branch": "ARTICLE_8_DUAL_COVERAGE"},
            "damage": {
                "vehicle_value": 2500,
                "actual_damage": 300,
                "corresponding_damage": 180,
                "policy_financial_limit": 200,
                "has_body_policy": True,
                "body_franchise_for_excess_disclosed": True,
            },
        },
        kb,
    )
    assert "G_NO_MANDATORY_FRANCHISE_WITHOUT_DISCLOSURE" in disclosed.guards_executed
    assert "regulatory_mandatory_franchise_on_this_excess" not in disclosed.fields
