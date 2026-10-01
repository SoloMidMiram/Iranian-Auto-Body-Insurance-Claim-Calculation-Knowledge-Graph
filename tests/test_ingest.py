"""Ingestion gate: schema closure, hierarchy resolution and the write brakes."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from iran_auto_claim.ingest import (
    apply_ingest,
    detect_contradictions,
    plan_ingest,
    validate_submission,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SUBMISSIONS = REPO_ROOT / "submissions"


def _submission(**overrides):
    base = {
        "node_id": "TEST_NEW_RULE",
        "source_class": "REGULATION",
        "authority": "High Insurance Council",
        "instrument": "Regulation 99",
        "article": "1",
        "effective_version": "current",
        "effective_date": "1405/01/01",
        "rule_payload": {"some_new_fact": True},
        "confidence": 0.9,
        "evidence_url": "https://example.invalid/regulation-99",
        "submitted_by": "tester",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------- schema gate


def test_a_well_formed_submission_passes_the_schema(kb):
    assert validate_submission(_submission(), kb) == []


@pytest.mark.parametrize(
    "field", ["node_id", "source_class", "authority", "instrument", "article", "confidence", "evidence_url"]
)
def test_each_required_field_is_enforced(field, kb):
    issues = validate_submission(_submission(**{field: None}), kb)
    assert any(field in issue for issue in issues), issues


def test_the_ingestion_schema_is_closed(kb):
    issues = validate_submission(_submission(notes="free text smuggling"), kb)
    assert any("unknown field" in issue for issue in issues)


def test_duplicate_node_ids_are_refused(kb):
    issues = validate_submission(_submission(node_id="REG53_ART19_REPLACEMENT_PART_DEPRECIATION"), kb)
    assert any("already exists" in issue for issue in issues)


def test_unknown_source_class_is_refused(kb):
    issues = validate_submission(_submission(source_class="BLOG_POST"), kb)
    assert any("hierarchy" in issue for issue in issues)


def test_confidence_outside_the_unit_interval_is_refused(kb):
    assert any("outside" in issue for issue in validate_submission(_submission(confidence=1.4), kb))
    assert any("outside" in issue for issue in validate_submission(_submission(confidence=-0.1), kb))


def test_payload_referencing_an_unknown_operator_is_refused(kb):
    issues = validate_submission(_submission(rule_payload={"operator": "OP_MADE_UP"}), kb)
    assert any("unknown operator" in issue for issue in issues)


def test_a_submission_with_errors_is_not_planned_further(kb):
    plan = plan_ingest(_submission(confidence=5), kb)
    assert plan["ok"] is False
    assert plan["rule_node"] is None
    assert plan["contradictions"] == []


# -------------------------------------------------------- contradiction logic


def test_the_educational_depreciation_template_loses_to_the_regulation(kb):
    submission = json.loads((SUBMISSIONS / "example_conflicting_educational.json").read_text(encoding="utf-8"))
    findings = detect_contradictions(submission, kb)
    assert len(findings) == 1
    finding = findings[0]
    assert finding["decision"] == "REJECT_SUBMISSION"
    assert finding["resolution"] == "REJECT_CANDIDATE"
    assert finding["controlling_rule"] == "REG53_ART19_REPLACEMENT_PART_DEPRECIATION"
    assert finding["candidate_source_class"] == "EDUCATIONAL"
    assert set(finding["conflicting_payload_keys"]) == {"scope", "scope_is_consumables_only"}
    assert plan_ingest(submission, kb)["ok"] is False


def test_a_statute_amendment_supersedes_the_council_instruction(kb):
    submission = json.loads((SUBMISSIONS / "example_superseding_statute.json").read_text(encoding="utf-8"))
    findings = detect_contradictions(submission, kb)
    assert len(findings) == 1
    assert findings[0]["decision"] == "SUPERSEDE_EXISTING"
    assert findings[0]["controlling_rule"] == "HIC_ARTICLE8_CONVENTIONAL_DEFINITION"
    assert findings[0]["resolution"] == "ACCEPT_CANDIDATE"


def test_a_same_rank_conflict_escalates_instead_of_guessing(kb):
    submission = _submission(
        node_id="TEST_RIVAL_STATUTE",
        source_class="STATUTE",
        instrument="Compulsory Third-Party Insurance Law 1395",
        article="8",
        rule_payload={"minimum_financial_commitment_ratio_of_bodily": 0.03},
    )
    findings = detect_contradictions(submission, kb)
    assert findings, "the rival statute should be reconciled against the existing one"
    assert {finding["decision"] for finding in findings} == {"HUMAN_REVIEW_SAME_RANK"}
    assert all(finding["resolution"] == "UNRESOLVED" for finding in findings)


def test_a_mistyped_instrument_is_reported_as_a_near_miss_not_as_a_new_topic(kb):
    """Silently finding no contradiction is the dangerous outcome of this gate."""
    submission = _submission(
        node_id="TEST_TYPO_STATUTE",
        source_class="STATUTE",
        instrument="Compulsory Third-Party Insurance Law",
        article="8",
        rule_payload={"minimum_financial_commitment_ratio_of_bodily": 0.03},
    )
    assert detect_contradictions(submission, kb) == []

    plan = plan_ingest(submission, kb)
    assert plan["ok"] is True, "a near miss is a warning, not a refusal"
    assert plan["near_miss_topics"], "the near miss must be surfaced"
    assert any(
        miss["rule"] == "TPL_LAW_1395_ART8_MIN_FINANCIAL_COMMITMENT" for miss in plan["near_miss_topics"]
    )
    assert plan["warnings"], "a near miss must produce an explicit warning"


def test_an_agreeing_submission_creates_no_contradiction(kb):
    submission = _submission(
        node_id="TEST_RESTATEMENT",
        instrument="Regulation 53",
        article="19",
        rule_payload={"annual_rate": 0.05, "maximum_rate": 0.25},
    )
    assert detect_contradictions(submission, kb) == []


def test_an_unrelated_submission_creates_no_contradiction(kb):
    assert detect_contradictions(_submission(), kb) == []


def test_topic_matching_does_not_depend_on_a_declared_topic(kb):
    submission = _submission(
        node_id="TEST_TOPICLESS_RESTATEMENT",
        instrument="Regulation 53",
        article="19",
        rule_payload={"annual_rate": 0.09},
    )
    findings = detect_contradictions(submission, kb)
    assert findings and findings[0]["controlling_rule"] == "REG53_ART19_REPLACEMENT_PART_DEPRECIATION"


# ------------------------------------------------------------------ brakes


def test_write_refuses_a_submission_that_loses_to_a_higher_authority(tmp_path, kb):
    submission = json.loads((SUBMISSIONS / "example_conflicting_educational.json").read_text(encoding="utf-8"))
    working = _copy_graph(tmp_path)
    with pytest.raises(ValueError) as excinfo:
        apply_ingest(submission, working, allow_review=True)
    assert "refusing to ingest" in str(excinfo.value)


def test_write_refuses_a_flagged_contradiction_without_an_explicit_decision(tmp_path):
    working = _copy_graph(tmp_path)
    submission = json.loads((SUBMISSIONS / "example_superseding_statute.json").read_text(encoding="utf-8"))
    with pytest.raises(ValueError) as excinfo:
        apply_ingest(submission, working)
    assert "--accept-review" in str(excinfo.value)


def test_an_accepted_supersede_commits_and_forces_a_verified_migration(tmp_path):
    working = _copy_graph(tmp_path)
    submission = json.loads((SUBMISSIONS / "example_superseding_statute.json").read_text(encoding="utf-8"))
    report = apply_ingest(submission, working, allow_review=True, as_of="2026-09-18")

    assert report["rule_written"] == "STATUTE_ARTICLE8_CONVENTIONAL_DEFINITION_AMENDMENT"
    assert report["rules_marked_superseded"] == ["HIC_ARTICLE8_CONVENTIONAL_DEFINITION"]
    assert report["contradictions_written"]

    rewire = report["references_requiring_rewire"]
    assert "ARTICLE_8_NON_CONVENTIONAL" in rewire["branches"]
    assert "THIRD_PARTY_FINANCIAL" in rewire["branches"]

    reloaded = type(working).load(working.root)
    superseded = reloaded.rule("HIC_ARTICLE8_CONVENTIONAL_DEFINITION")
    assert superseded["status"] == "SUPERSEDED"
    assert superseded["superseded_by"] == "STATUTE_ARTICLE8_CONVENTIONAL_DEFINITION_AMENDMENT"
    assert reloaded.contradictions[report["contradictions_written"][0]]["resolution"] == "ACCEPT_CANDIDATE"

    # the graph is knowingly inconsistent until the references are migrated
    issues = reloaded.validate()
    assert issues
    assert all("superseded" in issue for issue in issues), issues

    _rewire_branches(
        working.root,
        rewire["branches"],
        old="HIC_ARTICLE8_CONVENTIONAL_DEFINITION",
        new="STATUTE_ARTICLE8_CONVENTIONAL_DEFINITION_AMENDMENT",
    )
    assert type(working).load(working.root).validate() == []


def test_a_clean_submission_commits_without_review(tmp_path):
    working = _copy_graph(tmp_path)
    submission = _submission(node_id="TEST_CLEAN_ADDITION")
    report = apply_ingest(submission, working, allow_review=False, as_of="2026-09-18")
    assert report["rule_written"] == "TEST_CLEAN_ADDITION"
    assert report["rules_marked_superseded"] == []

    reloaded = type(working).load(working.root)
    assert reloaded.validate() == []
    committed = reloaded.rule("TEST_CLEAN_ADDITION")
    assert committed["last_validated"] == "2026-09-18"
    assert committed["next_revalidation"] == "2027-09-18"
    assert committed["sources"] == ["SRC_SUBMITTED_TEST_CLEAN_ADDITION"]


def _copy_graph(tmp_path: Path):
    from iran_auto_claim.knowledge import Knowledge

    for name in ("ontology", "knowledge"):
        shutil.copytree(REPO_ROOT / name, tmp_path / name)
    # The tier ladder cites case ids from the validation corpus, so an isolated
    # graph copy must carry it too or validate() reports every case as unknown.
    shutil.copytree(REPO_ROOT / "fixtures", tmp_path / "fixtures")
    return Knowledge.load(tmp_path)


def _rewire_branches(root: Path, branch_ids: list[str], old: str, new: str) -> None:
    """Perform the reference migration a human would complete after a supersede."""
    path = root / "knowledge" / "branches.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    for branch in document["branches"]:
        if branch["branch"] not in branch_ids:
            continue
        for field in ("governed_by", "controlled_by"):
            branch[field] = [new if ref == old else ref for ref in branch.get(field) or []]
        if branch.get("base_rule") == old:
            branch["base_rule"] = new
    path.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
