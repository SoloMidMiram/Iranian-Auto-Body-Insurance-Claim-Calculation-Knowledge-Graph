"""The calculation admission boundary.

Every amount this engine produces must have passed a gate that admitted it. These
tests pin that invariant from both sides:

* no raw claim payload, ``Case``, or refused decision can reach ``compute()``;
* a payload edited after authorization is refused rather than recalculated;
* the review gate refuses to issue authorization on REFUSE and
  INSUFFICIENT_INFORMATION;
* an unresolved risk intensification (U15) blocks at the review gate *and* at the
  engine, so it cannot be settled at the full amount by either path;
* valid calculations still produce exactly the same amounts, now carrying the
  authorization provenance that produced them.
"""

from __future__ import annotations

import copy
import json
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest

from iran_auto_claim.admission import (
    AUTHORIZED_DECISIONS,
    ISSUER_INTERNAL_TEST,
    ISSUER_REVIEW,
    AuthorizationError,
    AuthorizationNotGranted,
    CalculationAuthorization,
    _issue_review_authorization,
    claim_hash,
)
from iran_auto_claim.case import Case
from iran_auto_claim.engine import compute
from iran_auto_claim.fixtures import _authorize_fixture_case
from iran_auto_claim.review import Review
from iran_auto_claim.schema_input import InputSchemaError

REPO = Path(__file__).resolve().parents[1]
CASES = REPO / "cases"

FULLCOVER = "review_t1_fullcover_partial.json"
REFUSED = "review_refuse_wrong_licence.json"
PENDING_THEFT = "review_t2_theft_pending.json"
UNDERINSURED = "review_t3_underinsured_partial.json"
GLASS_TERMS = "review_t4_glass_terms_missing.json"

#: T1 is the certified single-payable rung; these are its known-good numbers.
T1_PAYABLE = Decimal(1657000000)


def load(name: str) -> dict:
    return json.loads((CASES / name).read_text(encoding="utf-8"))


# ------------------------------------------------------- direct compute bypass


def test_a_raw_payload_cannot_reach_compute(kb):
    """The signature is the boundary: a dict is not an authorization."""
    payload = {
        "claim_id": "bypass",
        "unit": "IRR",
        "classification": {"branch": "PARTIAL_DAMAGE", "domain": "BODY"},
        "event": {"event_date": "1405/06/01"},
        "damage": {"gross": 1600, "depreciation": 0, "market": 2000, "insured": 2000},
        "coverage_gate": {"causal_relationship_established": True},
        "policy": {
            "policy_version": "TEST-v1",
            "multiple_insurance": {"state": "NO", "prior_compensation": 0},
            "franchise": {
                "mode": "ABSOLUTE",
                "absolute_irr": 100,
                "source": "POLICY",
                "source_reference": "test policy schedule",
                "source_version": "TEST-v1",
            },
        },
    }
    with pytest.raises(AuthorizationError) as caught:
        compute(payload, kb)
    assert "CalculationAuthorization" in str(caught.value)


def test_a_bare_case_object_cannot_reach_compute(kb):
    """A validated Case is still not proof of admission."""
    case = Case(
        {
            "claim_id": "bypass",
            "unit": "IRR",
            "classification": {"branch": "PARTIAL_DAMAGE", "domain": "BODY"},
            "event": {"event_date": "1405/06/01"},
            "damage": {"gross": 1600},
        }
    )
    with pytest.raises(AuthorizationError):
        compute(case, kb)


def test_a_none_authorization_cannot_reach_compute(kb):
    with pytest.raises(AuthorizationError):
        compute(None, kb)


def test_an_authorization_for_another_decision_cannot_be_forged_by_casting(kb):
    """Any object that is not the authorization type is refused before inspection."""

    class Impostor:
        case = None
        decision = "COMPUTE"
        claim_hash = "sha256:" + "0" * 64
        issuer = ISSUER_REVIEW

    with pytest.raises(AuthorizationError):
        compute(Impostor(), kb)


@pytest.mark.parametrize("issuer", [ISSUER_REVIEW, "FORGED_ISSUER"])
def test_constructing_the_domain_object_directly_does_not_authorize(kb, issuer):
    """Only Review.authorize receives the private issuance capability."""
    forged = CalculationAuthorization(
        decision="COMPUTE",
        issuer=issuer,
    )
    with pytest.raises(AuthorizationError) as caught:
        compute(forged, kb)
    assert "Review.authorize" in str(caught.value)


def test_internal_test_authorization_cannot_masquerade_as_review_gate(kb):
    payload = {
        "claim_id": "internal-issuer",
        "unit": "IRR",
        "classification": {"branch": "PARTIAL_DAMAGE", "domain": "BODY"},
        "event": {"event_date": "1405/06/01"},
        "damage": {"gross": 100},
    }
    authorization = _authorize_fixture_case(payload, kb)
    assert authorization.issuer == ISSUER_INTERNAL_TEST
    with pytest.raises(AuthorizationError):
        compute(replace(authorization, issuer=ISSUER_REVIEW), kb)


def test_internal_test_authorization_still_validates_the_claim_schema(kb):
    with pytest.raises(InputSchemaError):
        _authorize_fixture_case(
            {
                "claim_id": "invalid-internal-input",
                "unit": "IRR",
                "classification": {"branch": "PARTIAL_DAMAGE", "domain": "BODY"},
                "damage": {"gross": -1},
            },
            kb,
        )


# ---------------------------------------------------- refusal and insufficiency


def test_a_refused_file_cannot_produce_an_authorization(kb):
    review = Review.from_file(CASES / REFUSED, kb)
    assert review.decision()["decision"] == "REFUSE"
    with pytest.raises(AuthorizationNotGranted) as caught:
        review.authorize()
    assert "REFUSE" in str(caught.value)
    assert "WRONG_CLASS" in str(caught.value)
    assert review.calculate() is None


def test_an_insufficient_file_cannot_produce_an_authorization(kb):
    """Every rung that stops at INSUFFICIENT_INFORMATION must stay outside the engine."""
    for name in (PENDING_THEFT, GLASS_TERMS):
        review = Review.from_file(CASES / name, kb)
        assert review.decision()["decision"] == "INSUFFICIENT_INFORMATION", name
        with pytest.raises(AuthorizationNotGranted):
            review.authorize()
        assert review.calculate() is None


def test_a_missing_blocking_document_stops_before_authorization(kb):
    payload = load(FULLCOVER)
    payload["evidence_present"] = [
        item for item in payload["evidence_present"] if item != "EVT_POLICY_COPY"
    ]
    review = Review(payload, kb)
    assert "EVT_POLICY_COPY" in review.decision()["evidence_blocks"]
    with pytest.raises(AuthorizationNotGranted):
        review.authorize()


def test_an_authorization_carrying_a_refused_decision_is_refused_by_the_engine(kb):
    """Defence in depth: a hand-built REFUSE token cannot pass verify()."""
    authorization = _authorize_fixture_case(
        {
            "claim_id": "forged",
            "unit": "IRR",
            "classification": {"branch": "PARTIAL_DAMAGE", "domain": "BODY"},
            "event": {"event_date": "1405/06/01"},
            "damage": {"gross": 1600},
        },
        kb,
    )
    for decision in ("REFUSE", "INSUFFICIENT_INFORMATION", "NOT_A_DECISION"):
        with pytest.raises(AuthorizationError):
            compute(replace(authorization, decision=decision), kb)


def test_only_the_two_issuing_decisions_are_authorized():
    assert AUTHORIZED_DECISIONS == {"COMPUTE", "SCENARIO_SET"}


# ----------------------------------------------------------- payload immutability


def test_dataclasses_replace_cannot_retarget_an_authorization(kb):
    """The exact reviewed claim cannot be replaced while retaining its capability."""
    base = {
        "claim_id": "tamper",
        "unit": "IRR",
        "classification": {"branch": "PARTIAL_DAMAGE", "domain": "BODY"},
        "event": {"event_date": "1405/06/01"},
        "damage": {"gross": 1600, "depreciation": 0, "market": 2000, "insured": 2000},
        "coverage_gate": {"causal_relationship_established": True},
        "policy": {
            "policy_version": "TEST-v1",
            "multiple_insurance": {"state": "NO", "prior_compensation": 0},
            "franchise": {
                "mode": "ABSOLUTE",
                "absolute_irr": 100,
                "source": "POLICY",
                "source_reference": "test policy schedule",
                "source_version": "TEST-v1",
            },
        },
    }
    authorization = _authorize_fixture_case(base, kb)
    inflated = copy.deepcopy(base)
    inflated["claim_id"] = "retargeted"
    inflated["damage"]["gross"] = 999999
    with pytest.raises((TypeError, ValueError)):
        replace(
            authorization,
            case=Case(inflated),
            claim_hash=claim_hash(inflated),
        )

    # Even an unchanged replace() call creates an unissued object because the
    # private immutable grant is init=False and is not copied by dataclasses.
    with pytest.raises(AuthorizationError):
        compute(replace(authorization), kb)

    # the unedited payload is still admitted, and still gives the same answer
    assert compute(authorization, kb).payable == Decimal(1500)


def test_review_live_uncertainty_cannot_disappear_into_a_single_payable(kb):
    payload = {
        "claim_id": "authorization-uncertainty-reconciliation",
        "unit": "IRR",
        "classification": {"branch": "PARTIAL_DAMAGE", "domain": "BODY"},
        "event": {"event_date": "1405/06/01"},
        "damage": {
            "gross": 100,
            "depreciation": 0,
            "market": 100,
            "insured": 100,
        },
        "policy": {
            "policy_version": "TEST-v1",
            "franchise": {
                "mode": "ABSOLUTE",
                "absolute_irr": 10,
                "source": "POLICY",
                "source_reference": "test schedule",
                "source_version": "TEST-v1",
            },
        },
    }
    authorization = _issue_review_authorization(
        payload,
        decision="SCENARIO_SET",
        issued_at="2026-10-08T00:00:00+00:00",
        provenance={"live_uncertainties": ["U04_BATTERY_TIRE_CAP_VS_DEPRECIATION"]},
    )
    result = compute(authorization, kb)
    assert result.payable is None
    assert result.payable_scenarios == []
    assert result.status == "AUTHORIZED_UNCERTAINTY_UNRESOLVED"
    assert result.blocking_uncertainties == ["U04_BATTERY_TIRE_CAP_VS_DEPRECIATION"]
    assert result.fields["authorization_uncertainties_added"] == [
        "U04_BATTERY_TIRE_CAP_VS_DEPRECIATION"
    ]


@pytest.mark.parametrize(
    "view",
    ["damage", "policy", "coverage", "classification", "evidence"],
)
def test_mutating_a_detached_case_view_cannot_change_the_authorized_calculation(kb, view):
    authorization = Review.from_file(CASES / FULLCOVER, kb).authorize()
    expected = compute(authorization, kb).to_dict()
    detached = authorization.case

    if view == "damage":
        detached.damage["labor_irr"] = 1_400_000_000
    elif view == "policy":
        detached.policy["franchise"] = {
            "mode": "ABSOLUTE",
            "absolute_irr": 0,
            "source": "POLICY",
            "source_reference": "forged",
            "source_version": "forged",
        }
    elif view == "coverage":
        detached.coverage["risk_intensified"] = True
    elif view == "classification":
        detached.branch = "TOTAL_LOSS"
        detached.classification_declaration["branch"] = "TOTAL_LOSS"
    elif view == "evidence":
        detached.evidence["EVT_POLICY_COPY"] = False

    assert compute(authorization, kb).to_dict() == expected


def test_mutating_a_case_supplied_at_issuance_cannot_change_the_snapshot(kb):
    payload = Review.from_file(CASES / FULLCOVER, kb).case_payload()
    supplied = Case(copy.deepcopy(payload))
    authorization = _authorize_fixture_case(supplied, kb)
    expected = compute(authorization, kb).to_dict()

    supplied.raw["claim_id"] = "mutated-after-issue"
    supplied.damage["labor_irr"] = 1_400_000_000
    supplied.policy.clear()
    supplied.coverage["risk_intensified"] = True
    supplied.evidence.clear()

    assert compute(authorization, kb).to_dict() == expected


def test_the_authorization_hash_is_content_derived_and_order_insensitive():
    one = {"claim_id": "X", "unit": "IRR", "damage": {"gross": 10}}
    two = {"damage": {"gross": 10}, "unit": "IRR", "claim_id": "X"}
    assert claim_hash(one) == claim_hash(two)
    assert claim_hash(one).startswith("sha256:")
    assert claim_hash({**one, "damage": {"gross": 11}}) != claim_hash(one)


# ------------------------------------------------------------ U15 risk intensification


def test_an_unresolved_risk_intensification_blocks_at_the_review_gate(kb):
    """The hole this boundary closes: Q-S3-07=YES used to reach a full payable."""
    payload = load(FULLCOVER)
    payload["answers"]["Q-S3-07"] = "YES"
    review = Review(payload, kb)

    decision = review.decision()
    assert decision["decision"] == "INSUFFICIENT_INFORMATION"
    assert "RISK_INTENSIFICATION_PREMIUM_RATIO_UNRESOLVED" in decision["blocking_conditions"]
    assert "U15_RISK_INTENSIFICATION_PREMIUM_RATIO" in decision["live_uncertainties"]

    with pytest.raises(AuthorizationNotGranted) as caught:
        review.authorize()
    assert "RISK_INTENSIFICATION_PREMIUM_RATIO_UNRESOLVED" in str(caught.value)
    assert review.calculate() is None


def test_an_unresolved_risk_intensification_blocks_at_the_engine_too(kb):
    """Defence in depth: synthetic validation cannot settle an intensified risk."""
    payload = {
        "claim_id": "u15-direct",
        "unit": "IRR",
        "classification": {"branch": "PARTIAL_DAMAGE", "domain": "BODY"},
        "event": {"event_date": "1405/06/01"},
        "damage": {"gross": 1600},
        "coverage_gate": {
            "causal_relationship_established": True,
            "risk_intensified": True,
        },
        "policy": {
            "policy_version": "TEST-v1",
            "multiple_insurance": {"state": "NO", "prior_compensation": 0},
            "franchise": {
                "mode": "ABSOLUTE",
                "absolute_irr": 100,
                "source": "POLICY",
                "source_reference": "test policy schedule",
                "source_version": "TEST-v1",
            },
        },
    }
    result = compute(_authorize_fixture_case(payload, kb), kb)
    assert result.payable is None
    assert result.payable_scenarios == []
    assert result.status == "RISK_INTENSIFICATION_PREMIUM_RATIO_UNRESOLVED"
    assert result.blocking_uncertainties == ["U15_RISK_INTENSIFICATION_PREMIUM_RATIO"]
    # the candidates come from the graph node, not from a copy restated in code
    node = kb.uncertainty("U15_RISK_INTENSIFICATION_PREMIUM_RATIO")
    assert result.fields["candidate_scenarios"] == node["scenarios"]
    assert len(result.fields["candidate_scenarios"]) == 2


def test_a_negative_risk_intensification_answer_does_not_block(kb):
    """NO is a real answer: it must not turn every ordinary file into INSUFFICIENT."""
    payload = load(FULLCOVER)
    assert payload["answers"]["Q-S3-07"] == "NO"
    review = Review(payload, kb)
    assert review.decision()["decision"] == "COMPUTE"
    assert "U15_RISK_INTENSIFICATION_PREMIUM_RATIO" not in review.open_uncertainties()
    assert review.calculate().payable == T1_PAYABLE


def test_an_unknown_risk_intensification_answer_blocks_authorization(kb):
    """UNKNOWN binds no fact and therefore leaves a material hard gate open."""
    payload = load(FULLCOVER)
    payload["answers"]["Q-S3-07"] = "UNKNOWN"
    review = Review(payload, kb)
    assert not review.is_answered("Q-S3-07")
    assert review.slot_status("PS_RISK_INTENSIFICATION").status == "UNANSWERED"
    assert "U15_RISK_INTENSIFICATION_PREMIUM_RATIO" not in review.open_uncertainties()
    assert review.case_payload()["coverage_gate"].get("risk_intensified") is not True
    assert "Q-S3-07" in review.decision()["open_blocking_questions"]
    assert review.decision()["decision"] == "INSUFFICIENT_INFORMATION"
    with pytest.raises(AuthorizationNotGranted):
        review.authorize()


def test_an_omitted_risk_intensification_answer_blocks_authorization(kb):
    """Omission cannot be interpreted as a negative risk-intensification fact."""
    payload = load(FULLCOVER)
    del payload["answers"]["Q-S3-07"]
    review = Review(payload, kb)

    assert "Q-S3-07" in review.decision()["open_blocking_questions"]
    assert review.decision()["decision"] == "INSUFFICIENT_INFORMATION"
    with pytest.raises(AuthorizationNotGranted):
        review.authorize()


def test_risk_intensification_blocks_every_body_branch_at_the_engine(kb):
    """U15 affects all four body branches; none of them may settle with it live."""

    def policy(branch: str) -> dict:
        endorsements = ["GLASS_ONLY"] if branch == "GLASS_ONLY" else []
        return {
            "policy_version": "TEST-v1",
            "endorsements": endorsements,
            "multiple_insurance": {"state": "NO", "prior_compensation": 0},
            "franchise": {
                "mode": "ABSOLUTE",
                "absolute_irr": 100,
                "source": "POLICY",
                "source_reference": "test policy schedule",
                "source_version": "TEST-v1",
            },
        }

    cases = (
        ("PARTIAL_DAMAGE", {"gross": 1600}),
        (
            "TOTAL_LOSS",
            {
                "market": 2000,
                "insured": 2000,
                "repair": 1900,
                "rescue_for_threshold": 0,
            },
        ),
        ("GLASS_ONLY", {"gross": 1600}),
        (
            "THEFT",
            {
                "theft_type": "WHOLE_VEHICLE",
                "days_missing": 65,
                "market": 2000,
                "insured": 2000,
                "title_transferred": True,
            },
        ),
    )
    for branch, damage in cases:
        payload = {
            "claim_id": f"u15-{branch}",
            "unit": "IRR",
            "classification": {"branch": branch, "domain": "BODY"},
            "event": {"event_date": "1405/06/01"},
            "damage": damage,
            "coverage_gate": {
                "causal_relationship_established": True,
                "risk_intensified": True,
            },
            "policy": policy(branch),
        }
        result = compute(_authorize_fixture_case(payload, kb), kb)
        assert result.status == "RISK_INTENSIFICATION_PREMIUM_RATIO_UNRESOLVED", branch
        assert result.payable is None, branch
        assert result.payable_scenarios == [], branch
        assert result.blocking_uncertainties == [
            "U15_RISK_INTENSIFICATION_PREMIUM_RATIO"
        ], branch


# ------------------------------------------------------- unchanged valid results


def test_a_valid_review_still_issues_the_same_single_payable(kb):
    review = Review.from_file(CASES / FULLCOVER, kb)
    authorization = review.authorize()

    assert authorization.decision == "COMPUTE"
    assert authorization.issuer == ISSUER_REVIEW
    assert authorization.issued_at
    result = compute(authorization, kb)

    assert result.payable == T1_PAYABLE
    assert result.payable_scenarios == []
    assert result.formula_confidence == 0.95


def test_an_authorized_scenario_set_is_still_a_scenario_set(kb):
    """SCENARIO_SET authorizes calculation; it never collapses to one number."""
    review = Review.from_file(CASES / UNDERINSURED, kb)
    authorization = review.authorize()

    assert authorization.decision == "SCENARIO_SET"
    result = compute(authorization, kb)

    assert result.payable is None
    assert len(result.payable_scenarios) == 2
    assert result.status == "ORDER_UNRESOLVED"
    assert "U01_ARTICLE10_PARTIAL_ORDER" in result.blocking_uncertainties


def test_synthetic_validation_reproduces_the_review_payable(kb):
    """The segregated test producer preserves arithmetic and identifies itself."""
    review = Review.from_file(CASES / FULLCOVER, kb)
    payload = review.case_payload()

    reviewed = compute(review.authorize(), kb)
    synthetic = compute(_authorize_fixture_case(copy.deepcopy(payload), kb), kb)

    assert synthetic.payable == reviewed.payable == T1_PAYABLE
    assert reviewed.authorization["issuer"] == ISSUER_REVIEW
    assert reviewed.authorization["review_kind"] == "CLAIM_FILE"
    assert synthetic.authorization["issuer"] == ISSUER_INTERNAL_TEST
    assert synthetic.authorization["authorization_kind"] == "INTERNAL_TEST_DIRECT"
    assert synthetic.authorization["purpose"] == "P01-L50_SYNTHETIC_FIXTURE"


def test_the_fixture_corpus_is_unchanged_by_the_boundary(kb):
    from iran_auto_claim.fixtures import run_all

    report = run_all(kb)
    assert len(report) == 50
    assert all(entry["ok"] for entry in report), [
        (entry["id"], entry["problems"]) for entry in report if not entry["ok"]
    ]
    for entry in report:
        assert entry["result"].authorization["issuer"] == ISSUER_INTERNAL_TEST
        assert entry["result"].authorization["authorization_kind"] == "INTERNAL_TEST_DIRECT"


# ------------------------------------------------------------ provenance is kept


def test_authorization_provenance_is_preserved_into_the_result(kb):
    review = Review.from_file(CASES / FULLCOVER, kb)
    authorization = review.authorize()

    record = authorization.provenance_record()
    assert record["issuer"] == ISSUER_REVIEW
    assert record["decision"] == "COMPUTE"
    assert record["claim_hash"] == authorization.claim_hash
    assert record["tier"] == "T1"
    assert record["branch"] == "PARTIAL_DAMAGE"
    # Legacy dash-separated Shamsi input is now validated and selects the actual
    # occurrence day; it no longer substitutes the Iranian year's final day.
    assert record["snapshot_id"] == "BODY@1404/08/20"
    assert record["classification"]["outcome"] == "MATCH"
    assert record["policy_snapshot"]["franchise"]["source"] == "POLICY"
    assert record["live_uncertainties"] == []
    assert record["blocking_conditions"] == []

    result = compute(authorization, kb)
    assert result.payable == T1_PAYABLE
    assert result.authorization["claim_hash"] == authorization.claim_hash
    assert result.authorization["issuer"] == ISSUER_REVIEW


def test_compute_applies_the_review_issued_evidence_confidence_cap(kb):
    payload = load(FULLCOVER)
    payload["evidence_present"].remove("EVT_PHOTOS")
    review = Review(payload, kb)
    authorization = review.authorize()

    assert authorization.provenance_record()["evidence_confidence_cap"] == "0.8"
    result = compute(authorization, kb)

    assert result.payable == T1_PAYABLE
    assert result.formula_confidence == 0.8
    assert "EVIDENCE_CONFIDENCE_REDUCED" in result.labels
    reviewed = review.calculate()
    assert reviewed.payable == result.payable
    assert reviewed.formula_confidence == result.formula_confidence
    assert reviewed.labels == result.labels


def test_authorization_provenance_is_an_immutable_snapshot(kb):
    authorization = Review.from_file(CASES / FULLCOVER, kb).authorize()
    expected = authorization.provenance_record()

    detached = authorization.provenance_record()
    detached["reviewer"] = "forged-reviewer"
    detached["approved_overrides"].append({"forged": True})
    detached["classification"]["outcome"] = "FORGED"
    detached["policy_snapshot"]["franchise"]["rate"] = 1
    detached["issuer"] = ISSUER_INTERNAL_TEST
    detached["decision"] = "REFUSE"
    detached["claim_hash"] = "sha256:" + "0" * 64

    property_copy = authorization.provenance
    property_copy["reviewer"] = "another-forgery"

    assert authorization.provenance_record() == expected
    emitted = compute(authorization, kb).authorization
    assert emitted == expected
    assert emitted["issuer"] == ISSUER_REVIEW
    assert emitted["decision"] == "COMPUTE"
    assert emitted["claim_hash"] == authorization.claim_hash


def test_the_reviewer_identity_is_carried_when_the_file_names_one(kb):
    payload = load(FULLCOVER)
    payload["reviewed_by"] = "adjuster-07"
    payload["as_of"] = "1404-09-02"
    review = Review(payload, kb)
    record = review.authorize().provenance_record()
    assert record["reviewer"] == "adjuster-07"
    assert record["review_as_of"] == "1404-09-02"


def test_the_serialized_result_includes_the_authorization(kb):
    review = Review.from_file(CASES / FULLCOVER, kb)
    document = compute(review.authorize(), kb).to_dict()
    assert document["authorization"]["issuer"] == ISSUER_REVIEW
    assert document["authorization"]["claim_hash"].startswith("sha256:")
    json.dumps(document, default=str)


def test_an_authorization_is_immutable(kb):
    """A frozen dataclass cannot be reassigned, so a ticket cannot be upgraded in place."""
    from dataclasses import FrozenInstanceError

    authorization = _authorize_fixture_case(
        {
            "claim_id": "X",
            "unit": "IRR",
            "classification": {"branch": "PARTIAL_DAMAGE", "domain": "BODY"},
            "damage": {"gross": 0},
        },
        kb,
    )
    with pytest.raises(FrozenInstanceError):
        authorization.decision = "REFUSE"  # type: ignore[misc]


def test_verify_is_called_before_any_arithmetic(kb):
    """A dataclass clone loses its private grant before arithmetic can run."""
    payload = {
        "claim_id": "stale",
        "unit": "IRR",
        "classification": {"branch": "PARTIAL_DAMAGE", "domain": "BODY"},
        "event": {"event_date": "1405/06/01"},
        "damage": {"gross": 1600},
    }
    authorization = _authorize_fixture_case(payload, kb)
    stale = replace(authorization)
    with pytest.raises(AuthorizationError):
        compute(stale, kb)
