"""Interface smoke tests: every command must exit cleanly and print something."""

from __future__ import annotations

from pathlib import Path

import pytest

from iran_auto_claim.cli import main

REPO = Path(__file__).resolve().parents[1]

COMMANDS = [
    ["validate"],
    ["fixtures"],
    ["unknowns"],
    ["unknowns", "--all"],
    ["contradictions"],
    ["contradictions", "--topic", "ARTICLE_8_CALCULATION"],
    ["branch", "PARTIAL_DAMAGE"],
    ["branch", "GLASS_ONLY"],
    ["rule", "REG53_ART19_REPLACEMENT_PART_DEPRECIATION"],
    ["node", "OP_UNDERINSURANCE_RATIO"],
    ["node", "PARTIAL_DAMAGE"],
    ["params"],
    ["params", "--year", "1405"],
    ["operators"],
    ["sources"],
    ["queries"],
    ["calc", str(REPO / "cases" / "review_t1_fullcover_partial.json")],
    ["json", str(REPO / "cases" / "review_t3_underinsured_partial.json")],
    ["classify", str(REPO / "cases" / "example_partial_unresolved.json")],
]


@pytest.mark.parametrize("argv", COMMANDS, ids=lambda argv: " ".join(argv[:2]))
def test_command_succeeds_and_prints(argv, capsys):
    code = main(argv)
    captured = capsys.readouterr().out
    assert captured.strip(), f"{argv} printed nothing"
    assert code == 0, captured


def test_fixtures_command_reports_a_full_pass(capsys):
    assert main(["fixtures"]) == 0
    out = capsys.readouterr().out
    assert "50/50 fixtures passed" in out


def test_calc_renders_the_escalation_for_an_unresolved_case(capsys):
    assert main(["calc", str(REPO / "cases" / "review_t3_underinsured_partial.json")]) == 0
    out = capsys.readouterr().out
    assert "ESCALATION" in out
    assert "U01_ARTICLE10_PARTIAL_ORDER" in out
    assert "ORDER_UNRESOLVED" in out
    assert "SCENARIOS" in out


def test_calc_renders_a_single_payable_for_a_resolved_case(capsys):
    assert main(["calc", str(REPO / "cases" / "review_t1_fullcover_partial.json")]) == 0
    out = capsys.readouterr().out
    assert "PAYABLE" in out
    assert "SCENARIOS" not in out


def test_calc_rejects_a_raw_claim_that_has_not_passed_review(capsys):
    assert main(["calc", str(REPO / "cases" / "example_partial_resolved.json")]) == 1
    out = capsys.readouterr().out
    assert "review_not_authorized" in out or "unknown_field" in out


def test_unknown_node_is_reported(capsys):
    assert main(["node", "NOT_A_NODE"]) == 1
    assert "unknown node" in capsys.readouterr().out


def test_unknown_rule_is_reported(capsys):
    assert main(["rule", "NOT_A_RULE"]) == 1
    assert "unknown rule" in capsys.readouterr().out


def test_queries_answers_the_documented_patterns(capsys):
    assert main(["queries"]) == 0
    out = capsys.readouterr().out
    assert "HOW IS PARTIAL DAMAGE CALCULATED?" in out
    assert "IS GLASS DEPRECIATED?" in out
    assert "WHAT IS UNRESOLVED?" in out
    # an 8th-index car sits mid-schedule; a 10th-index car is pinned at the ceiling
    assert "rate=0.20" in out
    assert "rate=0.25" in out
    assert "rate=0" in out
    assert "amended amended" not in out
    assert "LAMP, GLASS per the regulation" not in out


def test_ingest_dry_run_blocks_the_educational_template(capsys):
    code = main(["ingest", str(REPO / "submissions" / "example_conflicting_educational.json")])
    out = capsys.readouterr().out
    assert code == 1, "a submission that loses to a regulation must not exit cleanly"
    assert "REJECT_SUBMISSION" in out
    assert "dry run: pass --write to commit" in out
