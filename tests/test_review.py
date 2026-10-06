"""The case-review layer: questionnaire, parameter selection, ladder, and handoff.

These tests are deliberately written against *files* (the same JSON the CLI reads)
rather than against fixtures built in code, because the point of the layer is that a
real claim file can be reviewed, handed to the engine, and re-checked by an adjuster
from the printed procedure alone.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from iran_auto_claim.schema_input import InputSchemaError
from iran_auto_claim.review import (
    DECISION_COMPUTE,
    DECISION_INSUFFICIENT,
    DECISION_REFUSE,
    DECISION_SCENARIO,
    Review,
    ladder_markdown,
    mermaid_architecture,
    mermaid_branch_tree,
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
    with pytest.raises(InputSchemaError) as caught:
        Review({"claim_id": "X", "unit": "IRR", "answers": {"Q-S99-99": "YES"}}, kb)
    assert caught.value.errors[0].code == "unknown_field"
    assert caught.value.errors[0].path == "answers.Q-S99-99"


def test_an_inadmissible_choice_is_refused(kb):
    with pytest.raises(InputSchemaError) as caught:
        Review({"claim_id": "X", "unit": "IRR", "answers": {"Q-S2-01": "METEORITE"}}, kb)
    assert caught.value.errors[0].code == "invalid_enum"


def test_a_non_numeric_money_answer_is_refused(kb):
    with pytest.raises(InputSchemaError) as caught:
        Review(
            {"claim_id": "X", "unit": "IRR", "answers": {"Q-S2-01": "COLLISION", "Q-S4-02": "about forty"}}, kb
        )
    assert caught.value.errors[0].code == "invalid_type"


def test_unknown_is_admissible_and_binds_nothing(kb):
    review = Review({"claim_id": "X", "unit": "IRR", "answers": {"Q-S2-01": "UNKNOWN"}}, kb)
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
    assert result.payable == Decimal("1657000000")
    assert result.payable_scenarios == []
    assert result.formula_confidence == 0.95
    assert "REG53_ART19_REPLACEMENT_PART_DEPRECIATION" in result.rule_trace


def test_the_derived_case_round_trips_through_the_engine(kb):
    """The reviewed payload is exactly the payload bound to the authorization."""
    review = Review.from_file(CASES / "review_t1_fullcover_partial.json", kb)
    payload = review.case_payload()
    assert payload["classification"]["branch"] == "PARTIAL_DAMAGE"
    assert payload["classification"]["domain"] == "BODY"
    assert payload["policy"]["franchise"]["source"] == "POLICY"
    assert payload["policy"]["multiple_insurance"] == {
        "state": "NO",
        "prior_compensation": 0,
    }

    authorization = review.authorize()
    recomputed = review.calculate()
    assert authorization.case.raw == payload
    assert recomputed.payable == Decimal("1657000000")
    assert recomputed.authorization["issuer"] == "REVIEW_GATE"
    assert recomputed.authorization["claim_hash"] == authorization.claim_hash


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


def test_a_missing_production_year_stops_before_zero_depreciation(kb):
    payload = load("review_t1_fullcover_partial.json")
    payload["answers"].pop("Q-S5-03")
    review = Review(payload, kb)

    decision = review.decision()
    assert decision["decision"] == DECISION_INSUFFICIENT
    assert "Q-S5-03" in decision["open_blocking_questions"]
    assert "Q-S5-03" not in decision["open_hard_questions"]
    assert review.calculate() is None


def test_missing_franchise_terms_are_incomplete_not_a_scenario(kb):
    payload = load("review_t1_fullcover_partial.json")
    for question_id in ("Q-S6-01", "Q-S6-02", "Q-S6-03", "Q-S6-04"):
        payload["answers"].pop(question_id)
    review = Review(payload, kb)

    decision = review.decision()
    assert decision["decision"] == DECISION_INSUFFICIENT
    assert "U02_FRANCHISE_BASE_SCHEDULES" in decision["live_uncertainties"]
    assert review.calculate() is None


def test_review_rejects_unsourced_zero_franchise_as_incomplete(kb):
    payload = load("review_t1_fullcover_partial.json")
    payload["answers"]["Q-S6-01"] = "ABSOLUTE"
    payload["answers"]["Q-S6-02"] = {
        "mode": "ABSOLUTE",
        "absolute_irr": 0,
        "source": "POLICY",
    }
    payload["answers"].pop("Q-S6-03")
    payload["answers"].pop("Q-S6-04")
    review = Review(payload, kb)
    decision = review.decision()
    assert decision["decision"] == DECISION_INSUFFICIENT
    assert "U02_FRANCHISE_BASE_SCHEDULES" in decision["live_uncertainties"]
    assert review.calculate() is None


def _without_evidence(name: str, item_id: str) -> dict:
    payload = load(name)
    payload["evidence_present"] = [item for item in payload["evidence_present"] if item != item_id]
    return payload


def test_a_blocking_document_stops_calculation(kb):
    review = Review(_without_evidence("review_t1_fullcover_partial.json", "EVT_POLICY_COPY"), kb)
    decision = review.decision()
    assert decision["decision"] == DECISION_INSUFFICIENT
    assert "EVT_POLICY_COPY" in decision["missing_evidence"]
    assert "EVT_POLICY_COPY" in decision["evidence_blocks"]
    assert review.calculate() is None


def test_a_review_only_document_is_reported_and_still_calculated(kb):
    review = Review(_without_evidence("review_t1_fullcover_partial.json", "EVT_POLICE_CROQUIS"), kb)
    decision = review.decision()
    assert decision["decision"] == DECISION_COMPUTE
    assert "EVT_POLICE_CROQUIS" in decision["missing_evidence"]
    assert decision["evidence_blocks"] == []
    assert review.calculate().payable == Decimal("1657000000")


def test_a_confidence_document_caps_the_result_and_still_calculates(kb):
    review = Review(_without_evidence("review_t1_fullcover_partial.json", "EVT_PHOTOS"), kb)
    decision = review.decision()
    cap = kb.evidence_item("EVT_PHOTOS")["confidence_if_absent"]
    assert decision["decision"] == DECISION_COMPUTE
    assert "EVT_PHOTOS" in decision["missing_evidence"]
    result = review.calculate()
    assert result.payable == Decimal("1657000000")
    assert result.formula_confidence == cap
    assert "EVIDENCE_CONFIDENCE_REDUCED" in result.labels


def test_a_fractional_irr_labour_amount_is_rejected(kb):
    payload = load("review_t1_fullcover_partial.json")
    payload["answers"]["Q-S4-02"] = 40.9
    with pytest.raises(InputSchemaError) as caught:
        Review(payload, kb)
    assert caught.value.errors[0].code == "invalid_type"
    assert caught.value.errors[0].path == "answers.Q-S4-02"


# ----------------------------------------------------------------- other rungs


def test_the_underinsured_file_returns_scenarios_and_names_the_gap(kb):
    review = Review.from_file(CASES / "review_t3_underinsured_partial.json", kb)
    decision = review.decision()
    assert decision["decision"] == DECISION_SCENARIO
    assert decision["tier"] == "T3"
    assert decision["live_uncertainties"] == ["U01_ARTICLE10_PARTIAL_ORDER"]
    assert "EVT_POLICE_CROQUIS" in decision["missing_evidence"]
    assert "EVT_POLICE_CROQUIS" not in decision["evidence_blocks"]

    result = review.calculate()
    assert result.payable is None
    assert len(result.payable_scenarios) == 2
    assert result.formula_confidence == 0.55
    assert "UNDERINSURANCE_APPLIED" in result.labels


def test_the_pending_theft_file_stops_before_the_unanchored_clock_reaches_the_engine(kb):
    review = Review.from_file(CASES / "review_t2_theft_pending.json", kb)
    assert review.classification()["branch"] == "THEFT"
    assert review.tier()["assigned"] == "T2"
    assert review.decision()["decision"] == DECISION_INSUFFICIENT
    assert "U13_THEFT_CLOCK_ANCHOR" in review.open_uncertainties()
    assert review.calculate() is None


def test_overdue_instalment_is_unresolved_and_lapse_refuses_without_arithmetic(kb, monkeypatch):
    def unexpected_compute(*args, **kwargs):
        pytest.fail("a blocked policy must not reach the calculation engine")

    monkeypatch.setattr("iran_auto_claim.review.compute", unexpected_compute)
    for state, expected in (("INSTALMENT_OVERDUE", DECISION_INSUFFICIENT), ("LAPSED", DECISION_REFUSE)):
        payload = load("review_t1_fullcover_partial.json")
        payload["answers"]["Q-S0-06"] = state
        review = Review(payload, kb)
        decision = review.decision()
        assert decision["decision"] == expected
        if state == "INSTALMENT_OVERDUE":
            assert decision["refused_by"] == []
            assert decision["blocking_conditions"] == ["POLICY_CANCELLATION_STATUS_UNRESOLVED"]
        assert review.calculate() is None


def test_collision_and_fire_require_the_remaining_exclusion_answer(kb):
    for peril in ("COLLISION", "FIRE"):
        payload = load("review_t1_fullcover_partial.json")
        payload["answers"]["Q-S2-01"] = peril
        if peril == "FIRE":
            payload["answers"]["Q-S2-06"] = "REPORT_WITH_CAUSE"
            payload["evidence_present"].append("EVT_FIRE_CAUSE_REPORT")
        assert Review(payload, kb).decision()["decision"] == DECISION_COMPUTE
        payload["answers"].pop("Q-S3-04")
        review = Review(payload, kb)
        assert "Q-S3-04" in review.decision()["open_hard_questions"]
        assert review.decision()["decision"] == DECISION_INSUFFICIENT
        assert review.calculate() is None
        payload["answers"]["Q-S3-04"] = "OVERLOAD"
        assert Review(payload, kb).decision()["decision"] == DECISION_REFUSE


def test_no_stored_whole_theft_day_count_or_title_transfer_clears_u13(kb, monkeypatch):
    def unexpected_compute(*args, **kwargs):
        pytest.fail("an unanchored whole-theft clock must not reach the engine")

    monkeypatch.setattr("iran_auto_claim.review.compute", unexpected_compute)
    for days in (0, 38, 40, 55, 59, 60, 65, 70, 120):
        payload = load("review_t2_theft_pending.json")
        payload["answers"]["Q-S2-08"] = days
        payload["answers"]["Q-S4-06"] = "TRANSFERRED"
        review = Review(payload, kb)
        assert review.decision()["decision"] == DECISION_INSUFFICIENT
        assert "U13_THEFT_CLOCK_ANCHOR" in review.open_uncertainties()
        assert review.calculate() is None
        emitted = review.case_payload()
        assert emitted["damage"]["theft_type"] == "WHOLE_VEHICLE"
        assert "theft_type" not in emitted["event"]
        assert emitted["vehicle"]["title_transferred"] is True
    pending = Review.from_file(CASES / "review_t2_theft_pending.json", kb)
    assert pending.case_payload()["vehicle"]["title_transferred"] is False


def test_missing_event_year_stays_unknown_for_special_parts(kb):
    payload = load("review_t1_fullcover_partial.json")
    payload["answers"].pop("Q-S0-02")
    payload["answers"]["Q-S4-03"] = [{"category": "BATTERY", "assessed_loss": 120, "new_price": 200}]
    review = Review(payload, kb)
    assert review.slot_status("PS_CLAIM_YEAR").value is None
    assert "iranian_year" not in review.case_payload()["regulatory_snapshot"]
    assert "U04_BATTERY_TIRE_CAP_VS_DEPRECIATION" not in review.open_uncertainties()
    assert review.decision()["decision"] == DECISION_INSUFFICIENT
    assert review.calculate() is None


def test_emission_preserves_sourced_dates_causation_mode_ratio_and_year(kb):
    review = Review.from_file(CASES / "review_t1_fullcover_partial.json", kb)
    payload = review.case_payload()
    assert payload["event"]["awareness_date"] == "1404-08-20"
    assert payload["event"]["declaration_date"] == "1404-08-25"
    assert payload["coverage_gate"]["causal_relationship_established"] is True
    assert payload["calculation_config"]["settlement_mode"] == "CASH"
    assert payload["derived"]["article10_ratio"] == 1.0
    assert payload["regulatory_snapshot"]["iranian_year"] == 1404


def test_glass_with_other_damage_binds_after_the_later_part_list(kb):
    payload = load("review_t1_fullcover_partial.json")
    payload["answers"]["Q-S4-03"].append({"category": "GLASS", "assessed_loss": 10})
    payload["answers"]["Q-S2-05"] = "WITH_OTHER_DAMAGE"
    review = Review(payload, kb)
    assert review.slot_status("PS_GLASS_CAUSE_PRECEDENCE").value == "true"
    assert review.case_payload()["coverage_gate"]["glass_from_base_peril"] is True
    assert review.classification()["branch"] == "PARTIAL_DAMAGE"


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
        ("architecture", mermaid_architecture),
        ("branch-tree", mermaid_branch_tree),
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


def test_review_cli_writes_the_authorized_payload_but_calc_requires_the_review(capsys, tmp_path):
    from iran_auto_claim.cli import main

    emitted = tmp_path / "emitted.json"
    assert main(["review", str(CASES / "review_t1_fullcover_partial.json"), "--emit-case", str(emitted)]) == 0
    capsys.readouterr()
    payload = json.loads(emitted.read_text(encoding="utf-8"))
    assert payload["classification"]["domain"] == "BODY"
    assert main(["calc", str(emitted)]) == 1
    capsys.readouterr()
    assert main(["calc", str(CASES / "review_t1_fullcover_partial.json")]) == 0
    assert "165.70" in capsys.readouterr().out


def test_review_cli_refuses_an_unknown_question(capsys, tmp_path):
    from iran_auto_claim.cli import main

    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"claim_id": "X", "unit": "IRR", "answers": {"Q-S9-99": "YES"}}), encoding="utf-8")
    assert main(["review", str(bad)]) == 1
    error = json.loads(capsys.readouterr().out)
    assert error["errors"][0]["code"] == "unknown_field"
    assert error["errors"][0]["path"] == "answers.Q-S9-99"


def test_review_cli_does_not_export_an_unauthorized_case(capsys, tmp_path):
    from iran_auto_claim.cli import main

    emitted = tmp_path / "blocked.json"
    assert main(["review", str(CASES / "review_t0_intake_partial.json"), "--emit-case", str(emitted)]) == 1
    error = json.loads(capsys.readouterr().out)
    assert error["errors"][0]["code"] == "review_not_authorized"
    assert not emitted.exists()


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
