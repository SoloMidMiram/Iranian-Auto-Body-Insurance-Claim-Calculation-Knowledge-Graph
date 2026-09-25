"""The case-review layer: questionnaire, parameter selection, ladder, and handoff.

These tests are deliberately written against *files* (the same JSON the CLI reads)
rather than against fixtures built in code, because the point of the layer is that a
real claim file can be reviewed, handed to the engine, and re-checked by an adjuster
from the printed procedure alone.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from iran_auto_claim.case import Case
from iran_auto_claim.engine import compute
from iran_auto_claim.review import (
    DECISION_COMPUTE,
    DECISION_INSUFFICIENT,
    DECISION_REFUSE,
    DECISION_SCENARIO,
    Review,
    ReviewInputError,
    ladder_markdown,
    mermaid_flowchart,
    parameters_markdown,
    questionnaire_markdown,
)

REPO = Path(__file__).resolve().parents[1]
CASES = REPO / "cases"
DOC = REPO / "docs" / "BODY_CASE_REVIEW_MODEL.md"


def load(name: str) -> dict:
    return json.loads((CASES / name).read_text(encoding="utf-8"))


# --------------------------------------------------------------------- structure


def test_the_review_layer_is_registered_in_the_graph(kb):
    assert kb.stages and kb.questions and kb.slots and kb.tiers and kb.evidence
    assert len(kb.ordered_stages()) == 11
    # every question sits in a stage that exists and is ordered inside it
    for question in kb.questions.values():
        assert question["stage"] in kb.stages
        assert isinstance(question["order"], int)


def test_every_body_branch_declares_the_evidence_a_file_must_hold(kb):
    for branch in kb.branches.values():
        required = branch.get("required_evidence") or []
        assert required, f"{branch['branch']} names no evidence, so intake cannot be checked"
        for item_id in required:
            assert item_id in kb.evidence, f"{branch['branch']} -> unknown evidence {item_id}"


def test_a_questionnaire_answer_can_never_carry_an_amount(kb):
    """The boundary of the layer: questions select, they do not compute.

    A binding literal such as ``"value": 0.1`` would put a rate inside an intake form
    with no source at all, which is precisely the failure this model exists to prevent.
    """
    for question in kb.questions.values():
        for binding in question.get("sets") or []:
            literal = binding.get("value")
            assert not isinstance(literal, (int, float)), (
                f"{question['node_id']} binds the numeric literal {literal!r}; "
                "amounts must come from a policy slot with a named source"
            )


def test_every_slot_that_a_branch_requires_is_reachable(kb):
    """A required parameter must have a channel, or be derived from evidenced slots."""
    for branch_id, branch in kb.branches.items():
        if branch.get("domain") != "BODY":
            continue
        for slot in kb.slots_for_branch(branch_id):
            reachable = (
                kb.questions_filling_slot(slot["node_id"])
                or slot.get("supplied_by")
                or slot.get("authority") == "DERIVED"
            )
            assert reachable, f"{branch_id} needs {slot['node_id']} with no channel to fill it"


def test_a_predicate_naming_an_unknown_node_is_an_integrity_issue(kb):
    problems = kb._predicate_issues({"answer_is": ["Q-NOPE", "YES"]})
    assert any("unknown question" in problem for problem in problems)
    problems = kb._predicate_issues({"slot_present": "PS_NOT_A_SLOT"})
    assert any("unknown slot" in problem for problem in problems)
    problems = kb._predicate_issues({"branch_is": ["NOT_A_BRANCH"]})
    assert any("unknown branch" in problem for problem in problems)
    problems = kb._predicate_issues({"nonsense": True})
    assert any("unknown predicate key" in problem for problem in problems)


# --------------------------------------------------------------- answer hygiene


def test_an_unknown_question_is_refused_rather_than_ignored(kb):
    with pytest.raises(ReviewInputError, match="not a question in the procedure"):
        Review({"claim_id": "X", "answers": {"Q-S99-99": "YES"}}, kb)


def test_an_inadmissible_choice_is_refused(kb):
    with pytest.raises(ReviewInputError, match="is not admissible"):
        Review({"claim_id": "X", "answers": {"Q-S2-01": "METEORITE"}}, kb)


def test_a_non_numeric_money_answer_is_refused(kb):
    with pytest.raises(ReviewInputError, match="is not a money amount"):
        Review(
            {"claim_id": "X", "answers": {"Q-S2-01": "COLLISION", "Q-S4-02": "about forty"}}, kb
        )


def test_unknown_is_admissible_and_binds_nothing(kb):
    review = Review({"claim_id": "X", "answers": {"Q-S2-01": "UNKNOWN"}}, kb)
    assert not review.is_answered("Q-S2-01")
    assert review.slot_status("PS_PERIL").status == "UNANSWERED"


# ---------------------------------------------------------------- one clean file


def test_the_full_cover_partial_file_issues_exactly_one_number(kb):
    review = Review.from_file(CASES / "review_t1_fullcover_partial.json", kb)
    decision = review.decision()
    assert decision["decision"] == DECISION_COMPUTE
    assert decision["branch"] == "PARTIAL_DAMAGE"
    assert decision["tier"] == "T1"
    assert decision["missing_evidence"] == []
    assert review.open_uncertainties() == []

    result = review.calculate()
    assert result is not None
    # 185 gross, 12 depreciation on the depreciable part only (index 6 -> 10%),
    # 10% franchise after depreciation, rescue 10 under the 20% ceiling.
    assert float(result.payable) == pytest.approx(165.70)
    assert result.payable_scenarios == []
    assert result.formula_confidence == 0.95
    assert "REG53_ART19_REPLACEMENT_PART_DEPRECIATION" in result.rule_trace


def test_the_derived_case_round_trips_through_the_engine(kb):
    """What `--emit-case` writes must be readable by `calc` and give the same answer."""
    review = Review.from_file(CASES / "review_t1_fullcover_partial.json", kb)
    payload = review.case_payload()
    assert payload["classification"]["branch"] == "PARTIAL_DAMAGE"
    assert payload["classification"]["domain"] == "BODY"
    assert payload["policy"]["franchise"]["source"] == "POLICY"

    recomputed = compute(Case(copy.deepcopy(payload)), kb)
    assert recomputed.payable == review.calculate().payable


def test_questions_gated_off_by_earlier_answers_are_not_asked(kb):
    review = Review.from_file(CASES / "review_t1_fullcover_partial.json", kb)
    open_ids = {item["id"] for item in review.next_questions()}
    assert "Q-S4-04" not in open_ids, "no battery or tyre is damaged, so its new price is not needed"
    assert "Q-S4-08" not in open_ids, "the claim is not a total loss, so salvage is not asked"
    assert "Q-S8-02" not in open_ids, "the cap-versus-schedule collision cannot arise here"


def test_the_underinsurance_ratio_is_derived_and_not_asked(kb):
    review = Review.from_file(CASES / "review_t1_fullcover_partial.json", kb)
    binding = review.slot_status("PS_UNDERINSURANCE_RATIO")
    assert binding.status == "DERIVED"
    assert binding.value == pytest.approx(1.0)
    open_ids = {item["id"] for item in review.next_questions()}
    assert "Q-S8-01" not in open_ids, "the ratio is one, so the operator order cannot matter"


# ----------------------------------------------------------------- other rungs


def test_the_underinsured_file_returns_scenarios_and_names_the_gap(kb):
    review = Review.from_file(CASES / "review_t3_underinsured_partial.json", kb)
    decision = review.decision()
    assert decision["decision"] == DECISION_SCENARIO
    assert decision["tier"] == "T3"
    assert decision["live_uncertainties"] == ["U01_ARTICLE10_PARTIAL_ORDER"]

    result = review.calculate()
    assert result.payable is None
    assert len(result.payable_scenarios) == 2
    assert result.formula_confidence == 0.55
    assert "UNDERINSURANCE_APPLIED" in result.labels


def test_the_pending_theft_file_stops_at_the_sixty_day_criterion(kb):
    review = Review.from_file(CASES / "review_t2_theft_pending.json", kb)
    assert review.classification()["branch"] == "THEFT"
    assert review.tier()["assigned"] == "T2"
    result = review.calculate()
    assert result.payable is None
    assert result.status == "PENDING_60_DAY_CRITERION"


def test_a_missing_endorsement_schedule_is_named_not_guessed(kb):
    review = Review.from_file(CASES / "review_t4_glass_terms_missing.json", kb)
    decision = review.decision()
    assert decision["branch"] == "GLASS_ONLY"
    assert decision["decision"] == DECISION_INSUFFICIENT
    missing = {item["item"] for item in review.missing_evidence()}
    assert "EVT_ENDORSEMENT_WORDING" in missing
    assert "U03_GLASS_ONLY_ENDORSEMENT_WORDING" in review.open_uncertainties()
    assert review.calculate() is None


def test_an_intake_file_that_cannot_yet_classify_asks_for_the_earliest_stage(kb):
    review = Review.from_file(CASES / "review_t0_intake_partial.json", kb)
    decision = review.decision()
    assert decision["decision"] == DECISION_INSUFFICIENT
    # The procedure is front-loaded: S0 does not close until all three event dates are
    # in the file, so the next question must still belong to an early stage.
    first_open = review.next_questions(limit=1)[0]["id"]
    assert first_open.startswith(("Q-S0", "Q-S1")), first_open


def test_a_refusal_is_reached_before_any_arithmetic(kb):
    review = Review.from_file(CASES / "review_refuse_wrong_licence.json", kb)
    decision = review.decision()
    assert decision["decision"] == DECISION_REFUSE
    assert decision["refused_by"] == ["licence state WRONG_CLASS defeats cover (Q-S3-01)"]
    assert review.calculate() is None


def test_an_expired_license_is_not_treated_as_no_license(kb):
    """The regulation says an expired licence is not void; the review must agree."""
    payload = load("review_refuse_wrong_licence.json")
    payload["answers"]["Q-S3-01"] = "EXPIRED"
    review = Review(payload, kb)
    assert "licence state EXPIRED defeats cover (Q-S3-01)" not in review.refusal_reasons()
    assert review.case_payload()["event"]["valid_licence"] is True


def test_late_notice_is_a_review_gate_not_a_zero(kb):
    payload = load("review_t1_fullcover_partial.json")
    payload["answers"]["Q-S0-04"] = "LATE"
    review = Review(payload, kb)
    assert review.refusal_reasons() == []
    assert review.case_payload()["coverage_gate"]["late_notice_issue"] is True
    assert {item["item"] for item in review.missing_evidence()} >= {"EVT_LATE_NOTICE_EXCUSE"}


def test_the_ladder_reports_rungs_in_order_and_the_promotion_rule(kb):
    tiers = kb.ordered_tiers()
    assert [tier["node_id"] for tier in tiers] == ["T0", "T1", "T2", "T3", "T4", "T5", "T6"]
    assert kb.tiers_raw["promotion_rule"], "a ladder without a promotion rule is a list, not a gate"
    for tier in tiers:
        if tier.get("example_cases"):
            assert tier["permitted_outcomes"], tier["node_id"]


# ----------------------------------------------------------------- generated docs


@pytest.mark.parametrize(
    "marker, text",
    [
        ("flowchart", mermaid_flowchart),
        ("questionnaire", questionnaire_markdown),
        ("parameters", parameters_markdown),
        ("ladder", ladder_markdown),
    ],
)
def test_generated_blocks_in_the_document_match_the_graph(kb, marker, text):
    """The document embeds generated tables; if the graph changes, the doc fails CI."""
    assert DOC.exists(), "docs/BODY_CASE_REVIEW_MODEL.md must exist alongside the review layer"
    document = DOC.read_text(encoding="utf-8")
    begin = f"<!-- BEGIN GENERATED: {marker} -->"
    end = f"<!-- END GENERATED: {marker} -->"
    assert begin in document and end in document, f"{marker} block is missing from the document"
    embedded = document.split(begin, 1)[1].split(end, 1)[0].strip()
    assert embedded == text(kb).strip(), f"{marker} block is stale; run `claim.py {marker}`"


# -------------------------------------------------------------------------- CLI


def test_review_cli_states_the_decision_and_the_amount(capsys):
    from iran_auto_claim.cli import main

    assert main(["review", str(CASES / "review_t1_fullcover_partial.json")]) == 0
    printed = capsys.readouterr().out
    assert "Branch: PARTIAL_DAMAGE" in printed
    assert "ISSUE : COMPUTE" in printed
    assert "payable: 165.70 m-toman" in printed


def test_review_cli_writes_a_case_the_engine_accepts(capsys, tmp_path):
    from iran_auto_claim.cli import main

    emitted = tmp_path / "emitted.json"
    assert main(["review", str(CASES / "review_t1_fullcover_partial.json"), "--emit-case", str(emitted)]) == 0
    capsys.readouterr()
    payload = json.loads(emitted.read_text(encoding="utf-8"))
    assert payload["classification"]["domain"] == "BODY"
    assert main(["calc", str(emitted)]) == 0
    assert "165.70" in capsys.readouterr().out


def test_review_cli_refuses_an_unknown_question(capsys, tmp_path):
    from iran_auto_claim.cli import main

    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"claim_id": "X", "answers": {"Q-NOPE": "YES"}}), encoding="utf-8")
    assert main(["review", str(bad)]) == 1
    assert "not a question in the procedure" in capsys.readouterr().out


def test_review_cli_reports_readiness_as_json(capsys):
    from iran_auto_claim.cli import main

    assert main(["review", str(CASES / "review_t4_glass_terms_missing.json"), "--json"]) == 0
    document = json.loads(capsys.readouterr().out)
    assert document["decision"]["decision"] == DECISION_INSUFFICIENT
    assert document["calculation"] is None
    assert any(entry["item"] == "EVT_ENDORSEMENT_WORDING" for entry in document["missing_evidence"])


@pytest.mark.parametrize(
    "argv",
    [
        ["questionnaire"],
        ["questionnaire", "--stage", "S2_EVENT_CAUSATION"],
        ["questionnaire", "--format", "markdown"],
        ["parameters"],
        ["parameters", "--branch", "PARTIAL_DAMAGE"],
        ["parameters", "--format", "markdown"],
        ["ladder"],
        ["ladder", "--format", "markdown"],
        ["flowchart"],
    ],
)
def test_review_reference_commands_run_cleanly(capsys, argv):
    from iran_auto_claim.cli import main

    assert main(argv) == 0
    assert capsys.readouterr().out.strip()


def test_an_unknown_branch_is_reported_rather_than_printing_nothing(capsys):
    from iran_auto_claim.cli import main

    assert main(["parameters", "--branch", "NOT_A_BRANCH"]) == 1
    assert "no parameter slot" in capsys.readouterr().out
