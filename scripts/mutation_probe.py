"""Small dependency-free oracle used by the curated calculation mutation gate."""

from __future__ import annotations

import copy
import json
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

from iran_auto_claim.admission import (
    ISSUER_REVIEW,
    AuthorizationError,
    CalculationAuthorization,
    _canonical_json,
    _issue_review_authorization,
    claim_hash,
)
from iran_auto_claim.engine import (
    CalcResult,
    _dated_theft_clock_days,
    _enforce_guard_plan,
    compute,
)
from iran_auto_claim.fixtures import _authorize_fixture_case
from iran_auto_claim.knowledge import Knowledge
from iran_auto_claim.operators import (
    OperatorError,
    allowable_rescue_transport,
    eligible_part_loss,
    is_total_loss,
    underinsurance_ratio,
)
from iran_auto_claim.plans import (
    PlanError,
    graph_partial_payable,
    graph_total_loss_payable,
    validate_active_sequence,
)
from iran_auto_claim.review import Review


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

    probe_payload = {
        "claim_id": "mutation-probe",
        "unit": "IRR",
        "classification": {"branch": "PARTIAL_DAMAGE", "domain": "BODY"},
        "event": {"event_date": "1405/06/01"},
        "damage": {"gross": 1000},
        "coverage_gate": {"causal_relationship_established": True},
        "policy": {
            "multiple_insurance": {"state": "NO", "prior_compensation": 0}
        },
    }
    kb = Knowledge.load()
    authorization = _authorize_fixture_case(probe_payload, kb)

    try:
        compute(probe_payload, kb)
    except AuthorizationError:
        pass
    else:
        raise AssertionError("a raw claim payload reached compute without authorization")

    forged = CalculationAuthorization(
        decision="COMPUTE",
        issuer=ISSUER_REVIEW,
    )
    try:
        compute(forged, kb)
    except AuthorizationError:
        pass
    else:
        raise AssertionError("a directly constructed authorization passed the review seal")

    target_payload = {**probe_payload, "claim_id": "retargeted", "damage": {"gross": 999999}}
    target_grant = replace(
        authorization._grant,
        claim_snapshot=_canonical_json(target_payload),
        claim_hash=claim_hash(target_payload),
    )
    try:
        retargeted = replace(authorization, _grant=target_grant)
    except (TypeError, ValueError):
        pass
    else:
        try:
            compute(retargeted, kb)
        except AuthorizationError:
            pass
        else:
            raise AssertionError("dataclasses.replace transplanted the issuance capability")

    corrupted = copy.copy(authorization)
    object.__setattr__(
        corrupted,
        "_grant",
        replace(authorization._grant, claim_snapshot=_canonical_json(target_payload)),
    )
    try:
        compute(corrupted, kb)
    except AuthorizationError:
        pass
    else:
        raise AssertionError("a claim snapshot no longer matched its issued hash")

    masquerade = copy.copy(authorization)
    object.__setattr__(masquerade, "issuer", ISSUER_REVIEW)
    try:
        compute(masquerade, kb)
    except AuthorizationError:
        pass
    else:
        raise AssertionError("an internal authorization masqueraded as REVIEW_GATE")

    refused = copy.copy(authorization)
    object.__setattr__(refused, "decision", "REFUSE")
    object.__setattr__(refused, "_grant", replace(authorization._grant, decision="REFUSE"))
    try:
        compute(refused, kb)
    except AuthorizationError:
        pass
    else:
        raise AssertionError("a REFUSE decision reached the calculator")

    insufficient = copy.copy(authorization)
    object.__setattr__(insufficient, "decision", "INSUFFICIENT_INFORMATION")
    object.__setattr__(
        insufficient,
        "_grant",
        replace(authorization._grant, decision="INSUFFICIENT_INFORMATION"),
    )
    try:
        compute(insufficient, kb)
    except AuthorizationError:
        pass
    else:
        raise AssertionError("an INSUFFICIENT_INFORMATION decision reached the calculator")

    missing_franchise = compute(authorization, kb)
    assert missing_franchise.payable is None
    assert "U15_RISK_INTENSIFICATION_PREMIUM_RATIO" not in missing_franchise.blocking_uncertainties

    intensified = compute(
        _authorize_fixture_case(
            {
                **probe_payload,
                "coverage_gate": {
                    **probe_payload["coverage_gate"],
                    "risk_intensified": True,
                },
            },
            kb,
        ),
        kb,
    )
    assert intensified.payable is None
    assert intensified.status == "RISK_INTENSIFICATION_PREMIUM_RATIO_UNRESOLVED"
    assert "U15_RISK_INTENSIFICATION_PREMIUM_RATIO" in intensified.blocking_uncertainties

    # RMV-003: the effective depreciation is the change from capped eligible
    # loss to the selected one-pass result, not the scheduled amount deducted a
    # second time by the branch calculation.
    tire = {"category": "TIRE", "assessed_loss": Decimal(120), "new_price": Decimal(200)}
    tire_result = eligible_part_loss(
        tire,
        1392,
        1405,
        {"battery_tire_depreciation_interaction": "DEPRECIATE_THEN_CAP"},
    )
    assert tire_result["loss_after_depreciation"] == Decimal(90)
    assert tire_result["depreciation_amount"] == Decimal(10)

    repair_only = eligible_part_loss(
        {
            "category": "REPAIR_ONLY",
            "assessed_loss": Decimal(120),
            "new_price": None,
            "requires_replacement": False,
        },
        1399,
        1404,
    )
    assert repair_only["capped_loss"] == Decimal(120)
    assert repair_only["depreciation_amount"] == Decimal(0)

    review_payload = json.loads(
        (Path(__file__).resolve().parents[1] / "cases" / "review_t1_fullcover_partial.json").read_text(
            encoding="utf-8"
        )
    )
    review_payload["answers"]["Q-S5-01"] = 10000
    review_payload["answers"]["Q-S5-02"] = 10000
    review_payload["answers"]["Q-S5-03"] = 1404
    review_payload["answers"]["Q-S4-02"] = 0
    review_payload["answers"]["Q-S4-03"] = [
        {"category": "OTHER_REPLACEMENT_PART", "assessed_loss": 7400}
    ]
    review_payload["answers"]["Q-S4-07"] = 200
    assert Review(review_payload, kb).classification()["branch"] == "TOTAL_LOSS"

    sourced_absolute = {
        "mode": "ABSOLUTE",
        "absolute_irr": 10,
        "source": "POLICY",
        "source_reference": "mutation probe schedule",
        "source_version": "TEST-v1",
    }
    missing_rescue = {
        "claim_id": "missing-rescue-probe",
        "unit": "IRR",
        "classification": {
            "branch": "PARTIAL_DAMAGE",
            "domain": "BODY",
            "override": {
                "authorized": True,
                "actor": "mutation-probe-adjuster",
                "reason": "documented branch selection",
                "source": "mutation-probe-review-board",
                "timestamp": "2026-10-12T04:00:00Z",
            },
        },
        "event": {"event_date": "1405/06/01"},
        "coverage_gate": {"causal_relationship_established": True},
        "damage": {
            "gross": 7400,
            "repair": 7400,
            "market": 10000,
            "insured": 10000,
        },
        "policy": {
            "policy_version": "TEST-v1",
            "multiple_insurance": {"state": "NO", "prior_compensation": 0},
            "franchise": sourced_absolute,
        },
    }
    missing_rescue_result = compute(
        _authorize_fixture_case(missing_rescue, kb), kb
    )
    assert missing_rescue_result.payable is None
    assert missing_rescue_result.status == "CLASSIFICATION_EVIDENCE_REQUIRED"

    # M27 must remain observable without an override. An ordinary
    # evidence-derived threshold route cannot turn omitted rescue into zero.
    missing_rescue_without_override = copy.deepcopy(missing_rescue)
    missing_rescue_without_override["claim_id"] = "missing-rescue-no-override-probe"
    missing_rescue_without_override["classification"].pop("override")
    missing_rescue_without_override_result = compute(
        _authorize_fixture_case(missing_rescue_without_override, kb), kb
    )
    assert missing_rescue_without_override_result.payable is None
    assert (
        missing_rescue_without_override_result.status
        == "CLASSIFICATION_EVIDENCE_REQUIRED"
    )

    # A preliminary theft classification does not evaluate the repair/rescue
    # threshold. If an override selects a threshold-dependent final branch,
    # that candidate route must re-apply the missing-rescue evidence gate.
    override_from_theft = copy.deepcopy(missing_rescue)
    override_from_theft["claim_id"] = "override-from-theft-missing-rescue-probe"
    override_from_theft["damage"].update(
        {"theft_type": "WHOLE_VEHICLE", "days_missing": 10}
    )
    override_from_theft_result = compute(
        _authorize_fixture_case(override_from_theft, kb), kb
    )
    assert override_from_theft_result.payable is None
    assert override_from_theft_result.status == "CLASSIFICATION_EVIDENCE_REQUIRED"
    assert override_from_theft_result.fields["classification"]["derived_branch"] == "THEFT"

    override_without_repair = copy.deepcopy(override_from_theft)
    override_without_repair["claim_id"] = "override-from-theft-missing-repair-probe"
    override_without_repair["classification"]["branch"] = "TOTAL_LOSS"
    override_without_repair["damage"].pop("repair")
    override_without_repair["damage"]["rescue_for_threshold"] = 0
    override_without_repair_result = compute(
        _authorize_fixture_case(override_without_repair, kb), kb
    )
    assert override_without_repair_result.payable is None
    assert override_without_repair_result.status == "CLASSIFICATION_EVIDENCE_REQUIRED"
    assert "repair-and-replacement assessment" in override_without_repair_result.reason

    partial = {
        "claim_id": "runtime-defect-probe",
        "unit": "IRR",
        "classification": {"branch": "PARTIAL_DAMAGE", "domain": "BODY"},
        "event": {"event_date": "1405/06/01", "cause": "ALCOHOL"},
        "coverage_gate": {"causal_relationship_established": True},
        "damage": {
            "gross": 100,
            "depreciation": 20,
            "market": 100,
            "insured": 100,
        },
        "policy": {
            "policy_version": "TEST-v1",
            "multiple_insurance": {"state": "NO", "prior_compensation": 0},
            "franchise": sourced_absolute,
        },
    }

    # RMV-002: a coded intoxication cause without the causal authority flag is
    # insufficient to activate the non-compensable exclusion.
    causal = compute(_authorize_fixture_case(partial, kb), kb)
    assert causal.payable == Decimal(70)
    assert "exclusion_applied" not in causal.fields

    # RMV-004: AFTER_DEPRECIATION selects 80, not assessed gross 100.
    percentage = copy.deepcopy(partial)
    percentage["policy"]["franchise"] = {
        "mode": "PERCENT",
        "rate": 0.1,
        "calculation_base": "AFTER_DEPRECIATION",
        "source": "POLICY",
        "source_reference": "mutation probe schedule",
        "source_version": "TEST-v1",
    }
    percentage_result = compute(_authorize_fixture_case(percentage, kb), kb)
    assert percentage_result.fields["franchise"] == Decimal(8)
    assert percentage_result.payable == Decimal(72)

    # Total-loss SETTLEMENT_BASE is the pre-salvage min(market, insured), while
    # AFTER_SALVAGE is a genuinely different typed base when salvage is retained.
    total = {
        "claim_id": "total-loss-franchise-base-probe",
        "unit": "IRR",
        "classification": {"branch": "TOTAL_LOSS", "domain": "BODY"},
        "coverage_gate": {"causal_relationship_established": True},
        "damage": {
            "market": 2000,
            "insured": 2000,
            "repair": 1600,
            "rescue_for_threshold": 0,
            "salvage": 300,
            "salvage_disposition": "INSURED_RETAINS",
        },
        "policy": {
            "policy_version": "TEST-v1",
            "multiple_insurance": {"state": "NO", "prior_compensation": 0},
            "franchise": {
                "mode": "PERCENT",
                "rate": 0.1,
                "calculation_base": "SETTLEMENT_BASE",
                "source": "POLICY",
                "source_reference": "mutation probe schedule",
                "source_version": "TEST-v1",
            },
        },
    }
    total_settlement_base = compute(_authorize_fixture_case(total, kb), kb)
    assert total_settlement_base.fields["franchise"] == Decimal(200)
    total["policy"]["franchise"]["calculation_base"] = "AFTER_SALVAGE"
    total_after_salvage = compute(_authorize_fixture_case(total, kb), kb)
    assert total_after_salvage.fields["franchise"] == Decimal(170)

    insurer_title = copy.deepcopy(total)
    insurer_title["claim_id"] = "incomplete-title-transfer-probe"
    insurer_title["damage"]["salvage_disposition"] = "INSURER_TAKES_TITLE"
    insurer_title["damage"]["title_transferred"] = False
    insurer_title_result = compute(_authorize_fixture_case(insurer_title, kb), kb)
    assert insurer_title_result.payable is None
    assert insurer_title_result.status == "TITLE_TRANSFER_REQUIRED"
    assert (
        insurer_title_result.fields["guard_violation"]
        == "G_SALVAGE_XOR_TITLE_TRANSFER"
    )

    for disposition in (None, "NOT_APPLICABLE", "INSURED_RETAINS"):
        incomplete_salvage = copy.deepcopy(total)
        incomplete_salvage["damage"].pop("salvage", None)
        incomplete_salvage["damage"].pop("salvage_disposition", None)
        if disposition is not None:
            incomplete_salvage["damage"]["salvage_disposition"] = disposition
        blocked = compute(_authorize_fixture_case(incomplete_salvage, kb), kb)
        assert blocked.payable is None
        assert blocked.status in ("SALVAGE_DISPOSITION_UNRESOLVED", "SALVAGE_VALUE_REQUIRED")

    # The Shamsi clock accepts leap-year Esfand 30 and refuses it in a common
    # year; a permissive month-12 check would change theft eligibility.
    assert _dated_theft_clock_days(
        {
            "start_date": "1403-12-30",
            "as_of_date": "1404-01-01",
            "calendar": "SHAMSI",
        }
    ) == 1
    try:
        _dated_theft_clock_days(
            {
                "start_date": "1402-12-30",
                "as_of_date": "1403-01-01",
                "calendar": "SHAMSI",
            }
        )
    except OperatorError:
        pass
    else:
        raise AssertionError("non-leap Esfand 30 was accepted")

    # A selected declaration anchor cannot borrow the earlier occurrence date to
    # cross the sixty-day threshold before sixty declaration-based days elapsed.
    mismatched_theft_clock = {
        "claim_id": "theft-clock-event-date-probe",
        "unit": "IRR",
        "classification": {"branch": "THEFT"},
        "coverage_gate": {"causal_relationship_established": True},
        "policy": {
            "multiple_insurance": {"state": "NO", "prior_compensation": 0}
        },
        "damage": {
            "theft_type": "WHOLE_VEHICLE",
            "days_missing": 59,
        },
        "event": {
            "event_date": "1403-01-01",
            "declaration_date": "1403-01-02",
            "theft_clock": {
                "start_event": "DECLARATION",
                "start_date": "1403-01-01",
                "as_of_date": "1403-02-29",
                "calendar": "SHAMSI",
                "source": "mutation probe authority record",
            },
        },
    }
    mismatched_clock_result = compute(
        _authorize_fixture_case(mismatched_theft_clock, kb), kb
    )
    assert mismatched_clock_result.status == "INPUT_ERROR"
    assert "event.declaration_date" in mismatched_clock_result.reason

    # RMV-001: explicit zero is a real amount and caps Article 8 at zero.
    article8 = {
        "claim_id": "article8-zero-probe",
        "unit": "IRR",
        "classification": {"branch": "ARTICLE_8_NON_CONVENTIONAL"},
        "damage": {
            "vehicle_value": 2500,
            "actual_damage": 0,
            "corresponding_damage": 180,
            "policy_financial_limit": 200,
        },
    }
    article8_result = compute(_authorize_fixture_case(article8, kb), kb)
    assert article8_result.payable == Decimal(0)
    assert article8_result.fields["actual_damage"] == Decimal(0)

    # RMV-005: an authorization-live uncertainty may not disappear when the
    # arithmetic path itself does not rediscover it.
    review_authorization = _issue_review_authorization(
        partial,
        decision="SCENARIO_SET",
        issued_at="2026-10-08T00:00:00+00:00",
        provenance={"live_uncertainties": ["U04_BATTERY_TIRE_CAP_VS_DEPRECIATION"]},
    )
    reconciled = compute(review_authorization, kb)
    assert reconciled.payable is None
    assert "U04_BATTERY_TIRE_CAP_VS_DEPRECIATION" in reconciled.blocking_uncertainties
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
