"""Knowledge expander: schema-first ingestion with contradiction detection.

The report's expandability requirement is that no rule enters the graph as free
text. A submission must be declared, validated against the operator/rule shapes
already in use, and checked against every existing rule on the same topic before
it is committed. This module implements that gate.

Two modes:

* ``validate_submission`` / ``plan_ingest``  - dry run, always safe, returns the
  decision and the Contradiction node that would be created.
* ``apply_ingest``                           - writes the rule (and any
  contradiction node) into the knowledge files. Only reachable through the CLI's
  explicit ``--write`` flag.
"""

from __future__ import annotations

import json
import re
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from .knowledge import SOURCE_CLASSES, Knowledge, _read_json

REQUIRED_SUBMISSION_FIELDS = (
    "node_id",
    "source_class",
    "authority",
    "instrument",
    "article",
    "effective_version",
    "effective_date",
    "rule_payload",
    "confidence",
    "evidence_url",
    "submitted_by",
)

OPTIONAL_SUBMISSION_FIELDS = (
    "derivation",
    "derived_from",
    "applies_to_branches",
    "sources",
    "topic",
    "supersedes",
)


def validate_submission(submission: dict[str, Any], kb: Knowledge | None = None) -> list[str]:
    """Validate a new-rule submission against the ingestion schema."""
    issues: list[str] = []

    for field in REQUIRED_SUBMISSION_FIELDS:
        if submission.get(field) in (None, "", [], {}):
            issues.append(f"missing required field {field!r}")

    unknown = set(submission) - set(REQUIRED_SUBMISSION_FIELDS) - set(OPTIONAL_SUBMISSION_FIELDS)
    for field in sorted(unknown):
        issues.append(f"unknown field {field!r} (the ingestion schema is closed)")

    if submission.get("source_class") not in SOURCE_CLASSES:
        issues.append(f"source_class {submission.get('source_class')!r} is not in the hierarchy")

    confidence = submission.get("confidence")
    if confidence is not None:
        try:
            if not 0 <= float(confidence) <= 1:
                issues.append(f"confidence {confidence} outside [0, 1]")
        except (TypeError, ValueError):
            issues.append(f"confidence {confidence!r} is not a number")

    payload = submission.get("rule_payload")
    if payload is not None and not isinstance(payload, dict):
        issues.append("rule_payload must be an object")

    if kb is not None:
        if submission.get("node_id") in kb.all_ids:
            issues.append(f"node_id {submission.get('node_id')!r} already exists in the graph")
        for branch in submission.get("applies_to_branches") or []:
            if branch not in kb.branches:
                issues.append(f"applies_to_branches -> unknown branch {branch!r}")
        for dependency in submission.get("derived_from") or []:
            if dependency not in kb.rules:
                issues.append(f"derived_from -> unknown rule {dependency!r}")
        operator = (payload or {}).get("operator")
        if operator is not None and operator not in kb.operators:
            issues.append(f"rule_payload.operator -> unknown operator {operator!r}")

    return issues


def _shared_payload_keys(left: dict[str, Any], right: dict[str, Any]) -> set[str]:
    return {key for key in left if key in right}


def _conflicts(left: dict[str, Any], right: dict[str, Any], keys: set[str]) -> list[str]:
    conflicts: list[str] = []
    for key in sorted(keys):
        a, b = left[key], right[key]
        if isinstance(a, (int, float, bool, str)) and isinstance(b, (int, float, bool, str)):
            if a != b:
                conflicts.append(key)
    return conflicts


def _normalize(text: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(text or "").lower()).strip()


def near_miss_topics(submission: dict[str, Any], kb: Knowledge, limit: int = 5) -> list[dict[str, Any]]:
    """Existing rules that share part of the submission's identity but not all of it.

    Silently finding no contradiction is the dangerous outcome of an ingestion
    gate, because it looks identical to "this rule is genuinely new". A
    submission whose instrument string differs from an existing rule by a year
    suffix is far more likely to be a mistyped identifier than a new topic, so
    that case is reported rather than passed over.
    """
    submission_instrument = _normalize(submission.get("instrument"))
    submission_article = _normalize(submission.get("article"))
    findings: list[dict[str, Any]] = []

    for rule_id, rule in kb.rules.items():
        if same_topic(submission, rule):
            continue
        rule_instrument = _normalize(rule.get("instrument"))
        instrument_overlap = bool(submission_instrument and rule_instrument) and (
            submission_instrument in rule_instrument or rule_instrument in submission_instrument
        )
        article_matches = bool(submission_article) and submission_article == _normalize(rule.get("article"))
        if not (instrument_overlap or article_matches):
            continue
        findings.append(
            {
                "rule": rule_id,
                "instrument": rule.get("instrument"),
                "article": rule.get("article"),
                "reason": "instrument_string_differs" if instrument_overlap else "article_matches",
            }
        )
    return findings[:limit]


def _identity(node: dict[str, Any]) -> str:
    return f"instrument:{node.get('instrument')}::article:{node.get('article')}"


def same_topic(left: dict[str, Any], right: dict[str, Any]) -> bool:
    """Two rules share a topic when their declared topics agree, or their
    instrument+article identities agree.

    A declared topic is an *additional* matching key, never a replacement for the
    identity: a submission that names a topic no existing rule declares must still
    be reconciled against the instrument it claims to interpret.
    """
    left_topic = left.get("topic")
    right_topic = right.get("topic")
    if left_topic and right_topic and left_topic == right_topic:
        return True
    return _identity(left) == _identity(right)


def detect_contradictions(submission: dict[str, Any], kb: Knowledge) -> list[dict[str, Any]]:
    """Find existing rules on the same topic whose payload the submission changes.

    "Same topic" is defined mechanically (see same_topic), and a contradiction is
    a shared payload key whose value differs. That pair of conditions is the
    observable signature of a competing rule.
    """
    payload = submission.get("rule_payload") or {}
    findings: list[dict[str, Any]] = []

    for rule_id, rule in kb.rules.items():
        existing_payload = rule.get("rule_payload") or {}
        keys = _shared_payload_keys(payload, existing_payload)
        if not keys:
            continue
        if not same_topic(submission, rule):
            continue
        conflicts = _conflicts(payload, existing_payload, keys)
        if not conflicts:
            continue

        new_rank = kb.source_class_rank.get(submission.get("source_class"))
        old_rank = kb.source_class_rank.get(rule.get("source_class"))
        if new_rank is None or old_rank is None:
            decision = "HUMAN_REVIEW"
        elif new_rank < old_rank:
            # lower rank number == higher authority, so the new rule supersedes
            decision = "SUPERSEDE_EXISTING"
        elif new_rank > old_rank:
            decision = "REJECT_SUBMISSION"
        else:
            decision = "HUMAN_REVIEW_SAME_RANK"

        findings.append(
            {
                "contradiction_id": f"C_AUTO_{submission.get('node_id')}_VS_{rule_id}",
                "topic": rule.get("topic") or _identity(rule),
                "candidate_rule": submission.get("node_id"),
                "candidate_source_class": submission.get("source_class"),
                "controlling_rule": rule_id,
                "controlling_source_class": rule.get("source_class"),
                "conflicting_payload_keys": conflicts,
                "resolution": {
                    "SUPERSEDE_EXISTING": "ACCEPT_CANDIDATE",
                    "REJECT_SUBMISSION": "REJECT_CANDIDATE",
                    "HUMAN_REVIEW": "UNRESOLVED",
                    "HUMAN_REVIEW_SAME_RANK": "UNRESOLVED",
                }[decision],
                "decision": decision,
                "requires_human_review": True,
                "confidence": confidence_for_decision(new_rank, old_rank),
            }
        )
    return findings


def confidence_for_decision(new_rank: int | None, old_rank: int | None) -> float:
    if new_rank is None or old_rank is None:
        return 0.5
    if new_rank == old_rank:
        return 0.5
    return 0.98


def plan_ingest(
    submission: dict[str, Any], kb: Knowledge, as_of: str | None = None
) -> dict[str, Any]:
    """Dry run: what would be committed, and why."""
    issues = validate_submission(submission, kb)
    contradictions = [] if issues else detect_contradictions(submission, kb)
    blocked = [c for c in contradictions if c["decision"] == "REJECT_SUBMISSION"]
    review = [c for c in contradictions if c["requires_human_review"]]
    misses = [] if (issues or contradictions) else near_miss_topics(submission, kb)
    warnings = []
    if misses:
        warnings.append(
            "no contradiction detected, but "
            f"{len(misses)} existing rule(s) share part of this identity; confirm the instrument "
            "and article strings before committing, or declare an explicit topic"
        )
    return {
        "node_id": submission.get("node_id"),
        "ok": not issues and not blocked,
        "errors": issues,
        "warnings": warnings,
        "contradictions": contradictions,
        "near_miss_topics": misses,
        "blocked_by_hierarchy": [c["controlling_rule"] for c in blocked],
        "needs_human_review": [c["contradiction_id"] for c in review],
        "requires_review_confirmation": bool(review),
        "rule_node": _rule_node(submission, as_of) if not issues else None,
        "source_node": _source_node(submission, as_of),
    }


def _rule_node(submission: dict[str, Any], as_of: str | None = None) -> dict[str, Any]:
    """Build the committed rule node, including the validation cycle the graph requires."""
    validated_on = as_of or date.today().isoformat()
    try:
        next_cycle = (date.fromisoformat(validated_on) + timedelta(days=365)).isoformat()
    except ValueError:
        next_cycle = validated_on
    node = {
        "node_id": submission["node_id"],
        "source_class": submission["source_class"],
        "authority": submission["authority"],
        "instrument": submission["instrument"],
        "article": submission["article"],
        "effective_version": submission["effective_version"],
        "effective_date": submission["effective_date"],
        "confidence": submission["confidence"],
        "rule_payload": submission["rule_payload"],
        "sources": submission.get("sources") or [f"SRC_SUBMITTED_{submission['node_id']}"],
        "last_validated": validated_on,
        "next_revalidation": next_cycle,
    }
    for optional in ("derivation", "derived_from", "applies_to_branches", "topic"):
        if submission.get(optional) is not None:
            node[optional] = submission[optional]
    return node


def _source_node(submission: dict[str, Any], as_of: str | None = None) -> dict[str, Any]:
    return {
        "node_id": f"SRC_SUBMITTED_{submission.get('node_id')}",
        "title": f"Submitted evidence for {submission.get('node_id')}",
        "source_class": submission.get("source_class"),
        "authority": submission.get("authority"),
        "instrument": submission.get("instrument"),
        "article": submission.get("article"),
        "type": "SUBMITTED",
        "source_tier": "SUBMITTED_PENDING_REVIEW",
        "url": submission.get("evidence_url"),
        "retrieved_on": as_of or date.today().isoformat(),
        "submitted_by": submission.get("submitted_by"),
    }


def apply_ingest(
    submission: dict[str, Any], kb: Knowledge, allow_review: bool = False, as_of: str | None = None
) -> dict[str, Any]:
    """Commit a validated submission (and any contradiction nodes) to disk.

    Two independent brakes. A submission that loses to a higher-ranked source is
    refused outright. A submission that wins (or ties) still requires an explicit
    recorded human decision, because silently replacing a rule that the engine
    executes is not a side effect a schema check should be able to authorise.
    """
    plan = plan_ingest(submission, kb, as_of=as_of)
    if not plan["ok"]:
        raise ValueError(
            "refusing to ingest: " + "; ".join(plan["errors"] or plan["blocked_by_hierarchy"])
        )
    if plan["requires_review_confirmation"] and not allow_review:
        raise ValueError(
            "refusing to ingest: the submission contradicts existing rules and needs a recorded "
            "human decision ("
            + ", ".join(plan["needs_human_review"])
            + "); re-run with --accept-review once that decision is on file"
        )

    rules_path = kb.root / "knowledge" / "rules.json"
    sources_path = kb.root / "knowledge" / "sources.json"
    contradictions_path = kb.root / "knowledge" / "contradictions.json"

    rules_doc = _read_json(rules_path)
    rules_doc["rules"].append(plan["rule_node"])

    superseded: list[str] = []
    rewire_operators: list[str] = []
    rewire_branches: list[str] = []
    for finding in plan["contradictions"]:
        if finding["decision"] != "SUPERSEDE_EXISTING":
            continue
        target = finding["controlling_rule"]
        for existing in rules_doc["rules"]:
            if existing.get("node_id") != target:
                continue
            existing["status"] = "SUPERSEDED"
            existing["superseded_by"] = plan["rule_node"]["node_id"]
            existing["superseded_on"] = submission.get("effective_date")
            superseded.append(target)
        for operator_id, operator in kb.operators.items():
            if target in (operator.get("sourced_from") or []):
                rewire_operators.append(operator_id)
        for branch_id, branch in kb.branches.items():
            references = list(branch.get("governed_by") or [])
            references += list(branch.get("controlled_by") or [])
            if branch.get("base_rule"):
                references.append(branch["base_rule"])
            if target in references:
                rewire_branches.append(branch_id)

    rules_path.write_text(json.dumps(rules_doc, ensure_ascii=False, indent=2), encoding="utf-8")

    sources_doc = _read_json(sources_path)
    sources_doc["sources"].append(plan["source_node"])
    sources_path.write_text(json.dumps(sources_doc, ensure_ascii=False, indent=2), encoding="utf-8")

    written: list[str] = []
    if plan["contradictions"]:
        contradictions_doc = _read_json(contradictions_path)
        for finding in plan["contradictions"]:
            node = {
                "node_id": finding["contradiction_id"],
                "topic": finding["topic"],
                "candidate_rule": finding["candidate_rule"],
                "candidate_source_class": finding["candidate_source_class"],
                "controlling_rule": finding["controlling_rule"],
                "controlling_source_class": finding["controlling_source_class"],
                "resolution": finding["resolution"],
                "confidence": finding["confidence"],
                "decision": finding["decision"],
                "conflicting_payload_keys": finding["conflicting_payload_keys"],
                "requires_human_review": True,
            }
            contradictions_doc["contradictions"].append(node)
            written.append(node["node_id"])
        contradictions_path.write_text(
            json.dumps(contradictions_doc, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    return {
        "rule_written": plan["rule_node"]["node_id"],
        "source_written": plan["source_node"]["node_id"],
        "contradictions_written": written,
        "rules_marked_superseded": superseded,
        "references_requiring_rewire": {
            "operators": sorted(set(rewire_operators)),
            "branches": sorted(set(rewire_branches)),
        },
        "next_step": (
            "rewire the listed references to the superseding rule, then run `validate` "
            "(validation will keep failing while a reference still points at a superseded rule)"
            if (rewire_operators or rewire_branches)
            else "run `validate` to confirm graph integrity"
        ),
    }


def load_submission(path: Path | str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))
