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
    ISSUER_ENGINE_DIRECT,
    ISSUER_REVIEW,
    AuthorizationError,
    AuthorizationNotGranted,
    claim_hash,
    engine_direct_authorize,
)
from iran_auto_claim.case import Case
from iran_auto_claim.engine import compute
from iran_auto_claim.review import Review

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
        "damage": {"gross": 1600},
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
    authorization = engine_direct_authorize(
        {
            "claim_id": "forged",
            "unit": "IRR",
            "classification": {"branch": "PARTIAL_DAMAGE", "domain": "BODY"},
            "event": {"event_date": "1405/06/01"},
            "damage": {"gross": 1600},
        }
    )
    for decision in ("REFUSE", "INSUFFICIENT_INFORMATION", "NOT_A_DECISION"):
        with pytest.raises(AuthorizationError):
            compute(replace(authorization, decision=decision), kb)


def test_only_the_two_issuing_decisions_are_authorized():
    assert AUTHORIZED_DECISIONS == {"COMPUTE", "SCENARIO_SET"}


# ----------------------------------------------------------- payload immutability


def test_a_payload_edited_after_authorization_is_refused(kb):
    """Authorize a small claim, then try to calculate a large one on that ticket."""
    base = {
        "claim_id": "tamper",
        "unit": "IRR",
        "classification": {"branch": "PARTIAL_DAMAGE", "domain": "BODY"},
        "event": {"event_date": "1405/06/01"},
        "damage": {"gross": 1600},
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
    authorization = engine_direct_authorize(base, kb)
    inflated = copy.deepcopy(base)
    inflated["damage"]["gross"] = 999999
    with pytest.raises(AuthorizationError) as caught:
        compute(replace(authorization, case=Case(inflated)), kb)
    assert "hash" in str(caught.value)

    # the unedited payload is still admitted, and still gives the same answer
    assert compute(authorization, kb).payable == Decimal(1500)


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
    """Defence in depth: the direct channel cannot settle an intensified risk."""
    payload = {
        "claim_id": "u15-direct",
        "unit": "IRR",
        "classification": {"branch": "PARTIAL_DAMAGE", "domain": "BODY"},
        "event": {"event_date": "1405/06/01"},
        "damage": {"gross": 1600},
        "coverage_gate": {"risk_intensified": True},
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
    result = compute(engine_direct_authorize(payload, kb), kb)
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


def test_an_unknown_risk_intensification_answer_binds_nothing(kb):
    """UNKNOWN is a real answer that binds nothing, so no intensification is asserted.

    KNOWN GAP (reported, not silently fixed): because ``Q-S3-07`` is
    ``blocking: "review"``, an UNKNOWN or omitted answer leaves the file at
    COMPUTE and the engine issues the full amount. Closing that needs a
    knowledge-graph change to the question's blocking level plus a regeneration
    of the procedure tables, which is a review-policy decision beyond this
    boundary PR. The engine-side fail-closed only fires on an asserted ``true``.
    """
    payload = load(FULLCOVER)
    payload["answers"]["Q-S3-07"] = "UNKNOWN"
    review = Review(payload, kb)
    assert not review.is_answered("Q-S3-07")
    assert review.slot_status("PS_RISK_INTENSIFICATION").status == "UNANSWERED"
    assert "U15_RISK_INTENSIFICATION_PREMIUM_RATIO" not in review.open_uncertainties()
    assert review.case_payload()["coverage_gate"].get("risk_intensified") is not True


def test_risk_intensification_blocks_every_body_branch_at_the_engine(kb):
    """U15 affects all four body branches; none of them may settle with it live."""

    def policy(branch: str) -> dict:
        endorsements = ["GLASS_ONLY"] if branch == "GLASS_ONLY" else []
        return {
            "policy_version": "TEST-v1",
            "endorsements": endorsements,
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
        ("TOTAL_LOSS", {"market": 2000, "insured": 2000, "repair": 1900}),
        ("GLASS_ONLY", {"gross": 1600}),
    )
    for branch, damage in cases:
        payload = {
            "claim_id": f"u15-{branch}",
            "unit": "IRR",
            "classification": {"branch": branch, "domain": "BODY"},
            "event": {"event_date": "1405/06/01"},
            "damage": damage,
            "coverage_gate": {"risk_intensified": True},
            "policy": policy(branch),
        }
        result = compute(engine_direct_authorize(payload, kb), kb)
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


def test_the_direct_channel_reproduces_the_review_payable(kb):
    """Both producers must agree on the amount; only the issuer differs."""
    review = Review.from_file(CASES / FULLCOVER, kb)
    payload = review.case_payload()

    reviewed = compute(review.authorize(), kb)
    direct = compute(engine_direct_authorize(Case(copy.deepcopy(payload)), kb), kb)

    assert direct.payable == reviewed.payable == T1_PAYABLE
    assert reviewed.authorization["issuer"] == ISSUER_REVIEW
    assert direct.authorization["issuer"] == ISSUER_ENGINE_DIRECT


def test_the_fixture_corpus_is_unchanged_by_the_boundary(kb):
    from iran_auto_claim.fixtures import run_all

    report = run_all(kb)
    assert len(report) == 50
    assert all(entry["ok"] for entry in report), [
        (entry["id"], entry["problems"]) for entry in report if not entry["ok"]
    ]
    for entry in report:
        assert entry["result"].authorization["issuer"] == ISSUER_ENGINE_DIRECT


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
    # The T1 file dates are dash-separated, which the snapshot resolver does not
    # read as a Jalali anchor, so it falls back to the recorded Iranian year.
    assert record["snapshot_id"] == "BODY@1404/12/29"
    assert record["classification"]["outcome"] == "MATCH"
    assert record["policy_snapshot"]["franchise"]["source"] == "POLICY"
    assert record["live_uncertainties"] == []
    assert record["blocking_conditions"] == []

    result = compute(authorization, kb)
    assert result.authorization["claim_hash"] == authorization.claim_hash
    assert result.authorization["issuer"] == ISSUER_REVIEW


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


def test_an_authorization_is_immutable():
    """A frozen dataclass cannot be reassigned, so a ticket cannot be upgraded in place."""
    from dataclasses import FrozenInstanceError

    authorization = engine_direct_authorize({"claim_id": "X", "unit": "IRR"})
    with pytest.raises(FrozenInstanceError):
        authorization.decision = "REFUSE"  # type: ignore[misc]


def test_verify_is_called_before_any_arithmetic(kb):
    """A stale hash must fail even when the payload would calculate cleanly."""
    payload = {
        "claim_id": "stale",
        "unit": "IRR",
        "classification": {"branch": "PARTIAL_DAMAGE", "domain": "BODY"},
        "event": {"event_date": "1405/06/01"},
        "damage": {"gross": 1600},
    }
    authorization = engine_direct_authorize(payload, kb)
    stale = replace(authorization, claim_hash="sha256:" + "0" * 64)
    with pytest.raises(AuthorizationError):
        compute(stale, kb)
