"""Knowledge graph loading, querying and integrity validation.

The knowledge base is data. This module is the only thing that reads it, so
every graph query the CLI exposes goes through an index rather than a bespoke
scan. `validate()` is the schema-first ingestion gate: it is what an added node
must pass before it can be committed.
"""

from __future__ import annotations

import importlib
import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable

from .money import D

DEFAULT_ROOT = Path(__file__).resolve().parents[2]

SOURCE_CLASSES = ("STATUTE", "REGULATION", "CIRCULAR", "POLICY", "INSURER_PROCEDURE", "EDUCATIONAL")

OPERATOR_TYPES = (
    "DEPRECIATION",
    "FRANCHISE",
    "UNDERINSURANCE_RATIO",
    "SALVAGE_DEDUCTION",
    "RESCUE_CAP",
    "LIABILITY_CAP",
    "SPECIAL_PART_CAP",
    "CORRESPONDING_DAMAGE",
)

REQUIRED_RULE_FIELDS = (
    "node_id",
    "source_class",
    "authority",
    "instrument",
    "article",
    "effective_version",
    "effective_date",
    "rule_payload",
    "confidence",
    "last_validated",
    "next_revalidation",
)

REQUIRED_UNCERTAINTY_FIELDS = ("node_id", "topic", "blocking")

CONTROLLED_ORDER_STATUSES = ("RESOLVED", "UNRESOLVED", "INSURER_SPECIFIC", "ENDORSEMENT_DEPENDENT")

CONTRADICTION_RESOLUTIONS = (
    "REJECT_CANDIDATE",
    "ACCEPT_CANDIDATE",
    "ACCEPT_CANDIDATE_AS_INCOMPLETE",
    "UNRESOLVED",
)

# The review layer's own vocabularies. Each file also declares them at the top,
# so validate() checks the data against what the data itself promises.
ANSWER_FORMATS = ("choice", "list", "list_of_choices", "money", "integer", "date", "text")
REVIEW_BLOCKING_LEVELS = ("hard", "amount", "review", "not_blocking")
SLOT_AUTHORITIES = (
    "REGULATION",
    "CIRCULAR",
    "POLICY",
    "INSURER_PROCEDURE",
    "ASSESSOR",
    "ADJUSTER_CONFIG",
    "DERIVED",
    "EVENT_FACT",
)
SLOT_SUPPLY_CHANNELS = (
    "INSURED_ANSWER",
    "POLICY_SCHEDULE",
    "ENDORSEMENT_WORDING",
    "INSURER_MANUAL",
    "ASSESSOR_REPORT",
    "AUTHORITY_REPORT",
    "JUDICIAL_ORDER",
    "MARKET_EVIDENCE",
    "DERIVED_FROM_OTHER_SLOTS",
    "ANNUAL_PARAMETER",
    "ADJUSTER_CONFIG",
)
MISSING_BEHAVIOURS = (
    "DEFAULT_ONE",
    "TREAT_AS_ZERO",
    "REFUSE",
    "SCENARIO_SET",
    "ASSESSOR_REQUIRED",
    "ESCALATE_INSURER",
    "NOT_APPLICABLE",
    "REVIEW_GATE",
)
OUTCOME_CLASSES = (
    "SINGLE_PAYABLE",
    "SCENARIO_SET",
    "REFUSE",
    "PENDING",
    "ZERO_WITH_REASON",
    "ESCALATE_REVIEW",
    "NOT_CERTIFIED",
)
ABSENT_BEHAVIOURS = (
    "REFUSE_INTAKE",
    "BLOCK_PARAMETER",
    "ESCALATE_INSURER",
    "REDUCE_CONFIDENCE",
    "ROUTE_TO_REVIEW",
)
# Named derivations a questionnaire binding may request instead of a literal value.
SLOT_DERIVATIONS = ("iranian_year_of_event", "underinsurance_ratio", "depreciation_year_index")

# Reference fields that must resolve to a node of the given class. "ANY" means
# any node id in the graph, used where a contradiction may point at an operator,
# an uncertainty or an exclusion.
RESOLVABLE_FIELDS: tuple[tuple[str, str, str], ...] = (
    ("LegalRule", "sources", "Source"),
    ("LegalRule", "derived_from", "LegalRule"),
    ("LegalRule", "applies_to_branches", "Branch"),
    ("Operator", "sourced_from", "LegalRule"),
    ("Operator", "implied_uncertainties", "Uncertainty"),
    ("Operator", "annual_parameters", "AnnualParameter"),
    ("Operator", "applies_to_branches", "Branch"),
    ("Branch", "governed_by", "LegalRule"),
    ("Branch", "controlled_by", "LegalRule"),
    ("Branch", "base_rule", "LegalRule"),
    ("Branch", "operators", "Operator"),
    ("Branch", "blocking_uncertainties", "Uncertainty"),
    ("Branch", "guardrails", "Guardrail"),
    ("Uncertainty", "blocks", "Operator"),
    ("Uncertainty", "resolved_by", "Source"),
    ("Uncertainty", "affects_branches", "Branch"),
    ("Contradiction", "controlling_rule", "LegalRule"),
    ("Contradiction", "engine_uses", "ANY"),
    ("Contradiction", "guardrail", "Guardrail"),
    ("Exclusion", "sourced_from", "LegalRule"),
    ("Exclusion", "guardrail", "Guardrail"),
    ("AnnualParameter", "used_by", "Operator"),
    ("AnnualParameter", "derived_from", "AnnualParameter"),
    ("AnnualParameter", "sources", "Source"),
    ("Guardrail", "related_rules", "LegalRule"),
    ("Guardrail", "related_operators", "Operator"),
    ("Guardrail", "related_uncertainties", "Uncertainty"),
    # --- review layer -------------------------------------------------------
    ("ReviewQuestion", "stage", "ReviewStage"),
    ("ReviewQuestion", "requires_evidence", "EvidenceItem"),
    ("ReviewQuestion", "based_on", "LegalRule"),
    ("ReviewQuestion", "escalates_to", "Uncertainty"),
    ("ReviewQuestion", "guardrail", "Guardrail"),
    ("ReviewStage", "entry_from", "ReviewStage"),
    ("ReviewStage", "gate_evidence", "EvidenceItem"),
    ("EvidenceItem", "required_for_branches", "Branch"),
    ("EvidenceItem", "supplies_slots", "ParameterSlot"),
    ("EvidenceItem", "sourced_from", "LegalRule"),
    ("EvidenceItem", "stage", "ReviewStage"),
    ("ParameterSlot", "supplied_by", "ReviewQuestion"),
    ("ParameterSlot", "governed_by", "LegalRule"),
    ("ParameterSlot", "subject_to", "Operator"),
    ("ParameterSlot", "blocking_uncertainty", "Uncertainty"),
    ("ParameterSlot", "guardrail", "Guardrail"),
    ("ParameterSlot", "required_for_branches", "Branch"),
    ("ParameterSlot", "conditional_slots", "ParameterSlot"),
    ("CaseTier", "reachable_branches", "Branch"),
    ("CaseTier", "required_slots", "ParameterSlot"),
    ("CaseTier", "conditional_slots", "ParameterSlot"),
    ("CaseTier", "calibration_needed", "Uncertainty"),
    ("CaseTier", "next_tier", "CaseTier"),
    ("Branch", "required_evidence", "EvidenceItem"),
)

EDGE_BY_FIELD: dict[str, str] = {
    "sources": "belongs_to",
    "derived_from": "derived_from",
    "applies_to_branches": "governed_by",
    "sourced_from": "sourced_from",
    "implied_uncertainties": "implied_by",
    "annual_parameters": "used_by",
    "governed_by": "governed_by",
    "controlled_by": "governed_by",
    "base_rule": "governed_by",
    "operators": "composes",
    "blocking_uncertainties": "blocked_by",
    "guardrails": "guarded_by",
    "blocks": "blocks",
    "resolved_by": "resolved_by",
    "affects_branches": "affects",
    "controlling_rule": "about",
    "engine_uses": "uses",
    "used_by": "used_by",
    "related_rules": "about",
    "related_operators": "guards",
    "related_uncertainties": "guards",
    "restorable_by": "restores",
    # --- review layer -------------------------------------------------------
    "stage": "in_stage",
    "requires_evidence": "requires_evidence",
    "based_on": "based_on",
    "escalates_to": "escalates_to",
    "supplied_by": "supplied_by",
    "supplies_slots": "supplies_slot",
    "blocking_uncertainty": "blocked_by",
    "guardrail": "guarded_by",
    "required_for_branches": "required_for",
    "required_slots": "requires_parameter",
    "conditional_slots": "conditionally_requires_parameter",
    "calibration_needed": "calibrated_by",
    "next_tier": "next_tier",
    "entry_from": "entry_from",
    "gate_evidence": "gates_on_evidence",
}


@dataclass
class Node:
    """A typed view over a raw node dict, kept for callers that prefer attributes."""

    cls: str
    data: dict[str, Any]

    @property
    def id(self) -> str:
        return self.data.get("node_id") or self.data.get("branch") or "?"

    @property
    def confidence(self) -> float | None:
        value = self.data.get("confidence")
        return None if value is None else float(value)

    def __getitem__(self, key: str) -> Any:
        return self.data[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    @classmethod
    def of(cls, kb: "Knowledge", node_id: str) -> "Node | None":
        node, node_class = kb._locate(node_id)
        if node is None:
            return None
        return cls(cls=node_class or "Unknown", data=node)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"knowledge file missing: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:  # pragma: no cover - surfaced verbatim
        raise ValueError(f"{path}: invalid JSON at line {exc.lineno}: {exc.msg}") from exc


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


def resolve_callable(dotted: str) -> Any:
    module_name, _, attribute = dotted.rpartition(".")
    if not module_name:
        raise ImportError(f"{dotted!r} is not a dotted path")
    module = importlib.import_module(module_name)
    return getattr(module, attribute)


class Knowledge:
    """An indexed view of the knowledge graph."""

    def __init__(self, root: Path | str = DEFAULT_ROOT) -> None:
        self.root = Path(root)
        self.ontology = _read_json(self.root / "ontology" / "ontology.json")
        self.sources_raw = _read_json(self.root / "knowledge" / "sources.json")
        self.rules_raw = _read_json(self.root / "knowledge" / "rules.json")
        self.operators_raw = _read_json(self.root / "knowledge" / "operators.json")
        self.branches_raw = _read_json(self.root / "knowledge" / "branches.json")
        self.annual_raw = _read_json(self.root / "knowledge" / "annual_parameters.json")
        self.uncertainties_raw = _read_json(self.root / "knowledge" / "uncertainties.json")
        self.contradictions_raw = _read_json(self.root / "knowledge" / "contradictions.json")
        self.exclusions_raw = _read_json(self.root / "knowledge" / "exclusions.json")
        self.guards_raw = _read_json(self.root / "knowledge" / "guards.json")
        self.evidence_raw = _read_json(self.root / "knowledge" / "evidence_items.json")
        self.procedure_raw = _read_json(self.root / "knowledge" / "review_procedure.json")
        self.slots_raw = _read_json(self.root / "knowledge" / "parameter_slots.json")
        self.tiers_raw = _read_json(self.root / "knowledge" / "case_tiers.json")

        self.source_class_rank = {
            entry["id"]: int(entry["rank"]) for entry in self.ontology["source_class_hierarchy"]
        }
        self.branch_aliases: dict[str, dict[str, str]] = dict(
            self.ontology.get("branch_aliases", {}).get("aliases", {})
        )

        self.sources: dict[str, dict] = self._index(self.sources_raw["sources"], "node_id")
        self.rules: dict[str, dict] = self._index(self.rules_raw["rules"], "node_id")
        self.operators: dict[str, dict] = self._index(self.operators_raw["operators"], "node_id")
        self.branches: dict[str, dict] = self._index(self.branches_raw["branches"], "branch")
        self.annual: dict[str, dict] = self._index(self.annual_raw["parameters"], "node_id")
        self.uncertainties: dict[str, dict] = self._index(
            self.uncertainties_raw["uncertainties"], "node_id"
        )
        self.contradictions: dict[str, dict] = self._index(
            self.contradictions_raw["contradictions"], "node_id"
        )
        self.exclusions: dict[str, dict] = self._index(self.exclusions_raw["exclusions"], "node_id")
        self.guards: dict[str, dict] = self._index(self.guards_raw["guards"], "node_id")
        self.evidence: dict[str, dict] = self._index(self.evidence_raw["evidence"], "node_id")
        self.stages: dict[str, dict] = self._index(self.procedure_raw["stages"], "node_id")
        self.questions: dict[str, dict] = self._index(self.procedure_raw["questions"], "node_id")
        self.slots: dict[str, dict] = self._index(self.slots_raw["slots"], "node_id")
        self.tiers: dict[str, dict] = self._index(self.tiers_raw["tiers"], "node_id")

        self._registry_by_class: dict[str, dict[str, dict]] = {
            "Source": self.sources,
            "LegalRule": self.rules,
            "Operator": self.operators,
            "Branch": self.branches,
            "AnnualParameter": self.annual,
            "Uncertainty": self.uncertainties,
            "Contradiction": self.contradictions,
            "Exclusion": self.exclusions,
            "Guardrail": self.guards,
            "EvidenceItem": self.evidence,
            "ReviewStage": self.stages,
            "ReviewQuestion": self.questions,
            "ParameterSlot": self.slots,
            "CaseTier": self.tiers,
        }
        self.all_ids: set[str] = set()
        for registry in self._registry_by_class.values():
            self.all_ids.update(registry)

    @staticmethod
    def _index(items: Iterable[dict], id_key: str) -> dict[str, dict]:
        out: dict[str, dict] = {}
        for item in items:
            key = item.get(id_key)
            if key:
                out[key] = item
        return out

    @classmethod
    def load(cls, root: Path | str = DEFAULT_ROOT) -> "Knowledge":
        return cls(root)

    # ------------------------------------------------------------- accessors

    def rule(self, rule_id: str) -> dict | None:
        return self.rules.get(rule_id)

    def operator(self, operator_id: str) -> dict | None:
        return self.operators.get(operator_id)

    def branch(self, branch_id: str) -> dict | None:
        return self.branches.get(branch_id)

    def uncertainty(self, uncertainty_id: str) -> dict | None:
        return self.uncertainties.get(uncertainty_id)

    def source(self, source_id: str) -> dict | None:
        return self.sources.get(source_id)

    def canonical_branch(self, name: str) -> str:
        alias = self.branch_aliases.get(name)
        return alias["branch"] if alias else name

    def annual_parameter(self, year: int, name: str) -> dict | None:
        for node in self.annual.values():
            if int(node.get("year", 0)) == int(year) and node.get("name") == name:
                return node
        return None

    def annual_value(self, year: int, name: str) -> Decimal | None:
        node = self.annual_parameter(year, name)
        if node is None:
            return None
        return D(node["value"])

    def blocking_uncertainties(self) -> list[dict]:
        return [u for u in self.uncertainties.values() if u.get("blocking")]

    def rules_for_branch(self, branch_id: str) -> list[dict]:
        canonical = self.canonical_branch(branch_id)
        return [
            rule
            for rule in self.rules.values()
            if canonical in (rule.get("applies_to_branches") or [])
        ]

    def operators_for_branch(self, branch_id: str) -> list[dict]:
        info = self.branch(branch_id)
        if info is None:
            return []
        return [self.operators[oid] for oid in info.get("operators", []) if oid in self.operators]

    def body_branch_ids(self) -> list[str]:
        return sorted(
            branch_id
            for branch_id, node in self.branches.items()
            if node.get("domain") == "BODY"
        )

    def body_operator_scope(self) -> dict[str, list[str]]:
        """Body branches that list each operator. This is the branch scope."""
        scope: dict[str, list[str]] = {}
        for branch_id in self.body_branch_ids():
            for operator_id in self.branches[branch_id].get("operators") or []:
                scope.setdefault(str(operator_id), []).append(branch_id)
        return {operator_id: sorted(branches) for operator_id, branches in scope.items()}

    def body_operator_authority_register(self) -> list[dict[str, Any]]:
        """Chain operator → rule → source → authority class → effective date → branch scope.

        Source tiers are reported as stored. A mirror is not rewritten to PRIMARY.
        Missing reviewer text is a finding, not a correction.
        """
        rows: list[dict[str, Any]] = []
        for operator_id, branch_scope in self.body_operator_scope().items():
            operator = self.operators.get(operator_id)
            issues, findings = self._audit_body_operator(operator_id, operator, branch_scope)
            rows.append(
                {
                    "operator_id": operator_id,
                    "branch_scope": branch_scope,
                    "sourced_from": list((operator or {}).get("sourced_from") or []),
                    "issues": issues,
                    "findings": findings,
                }
            )
        return rows

    def body_operator_authority_issues(self) -> list[str]:
        issues: list[str] = []
        for row in self.body_operator_authority_register():
            issues.extend(
                f"operator {row['operator_id']}: {problem}" for problem in row["issues"]
            )
        return issues

    def body_operator_authority_findings(self) -> list[str]:
        findings: list[str] = []
        for row in self.body_operator_authority_register():
            findings.extend(
                f"operator {row['operator_id']}: {problem}" for problem in row["findings"]
            )
        return _unique(findings)

    def _audit_body_operator(
        self,
        operator_id: str,
        operator: dict[str, Any] | None,
        branch_scope: list[str],
    ) -> tuple[list[str], list[str]]:
        issues: list[str] = []
        findings: list[str] = []
        if not branch_scope:
            issues.append("no body branch scope")
        if operator is None:
            issues.append("operator node is missing")
            return issues, findings
        declared = sorted(
            branch_id
            for branch_id in operator.get("applies_to_branches") or []
            if (self.branches.get(branch_id) or {}).get("domain") == "BODY"
        )
        if declared != branch_scope:
            findings.append(
                "declared body branch list "
                f"{declared} differs from branches that compose it {branch_scope}; "
                "left unchanged"
            )
        rule_ids = [str(rule_id) for rule_id in operator.get("sourced_from") or []]
        if not rule_ids:
            issues.append("no sourced rule")
            return issues, findings
        for rule_id in rule_ids:
            rule = self.rules.get(rule_id)
            if rule is None:
                issues.append(f"sourced rule {rule_id} is missing")
                continue
            authority_class = rule.get("source_class")
            if authority_class not in self.source_class_rank:
                issues.append(f"rule {rule_id} has no authority class")
            if not rule.get("authority"):
                issues.append(f"rule {rule_id} has no authority")
            if not rule.get("effective_date"):
                issues.append(f"rule {rule_id} has no effective date")
            source_ids = [str(source_id) for source_id in rule.get("sources") or []]
            if not source_ids:
                issues.append(f"rule {rule_id} has no source")
            for source_id in source_ids:
                source = self.sources.get(source_id)
                if source is None:
                    issues.append(f"rule {rule_id} source {source_id} is missing")
                    continue
                tier = source.get("source_tier")
                if tier == "PRIMARY_MIRROR":
                    findings.append(
                        f"source {source_id} remains PRIMARY_MIRROR; tier was not upgraded"
                    )
                if not source.get("reviewer"):
                    findings.append(f"source {source_id} has no reviewer")
                note = str(source.get("access_note") or "").lower()
                if "timed out" in note or "not retrieved" in note or "was not retrieved" in note:
                    findings.append(
                        f"source {source_id} records that the official host was not retrieved"
                    )
        return issues, findings

    def contradictions_by_topic(self, topic: str) -> list[dict]:
        return [c for c in self.contradictions.values() if c.get("topic") == topic]

    # ------------------------------------------------------- review accessors

    def question(self, question_id: str) -> dict | None:
        return self.questions.get(question_id)

    def stage(self, stage_id: str) -> dict | None:
        return self.stages.get(stage_id)

    def slot(self, slot_id: str) -> dict | None:
        return self.slots.get(slot_id)

    def tier(self, tier_id: str) -> dict | None:
        return self.tiers.get(tier_id)

    def evidence_item(self, item_id: str) -> dict | None:
        return self.evidence.get(item_id)

    def ordered_stages(self) -> list[dict]:
        return sorted(self.stages.values(), key=lambda s: int(s.get("order", 0)))

    def ordered_questions(self) -> list[dict]:
        def key(node: dict) -> tuple[int, int, str]:
            stage = self.stages.get(node.get("stage") or "", {})
            return (int(stage.get("order", 99)), int(node.get("order", 99)), node["node_id"])

        return sorted(self.questions.values(), key=key)

    def questions_for_stage(self, stage_id: str) -> list[dict]:
        return [q for q in self.ordered_questions() if q.get("stage") == stage_id]

    def ordered_tiers(self) -> list[dict]:
        return sorted(self.tiers.values(), key=lambda t: int(t.get("rank", 99)))

    def slots_for_branch(self, branch_id: str) -> list[dict]:
        canonical = self.canonical_branch(branch_id)
        return [
            slot
            for slot in self.slots.values()
            if canonical in (slot.get("required_for_branches") or [])
        ]

    def questions_filling_slot(self, slot_id: str) -> list[dict]:
        found: list[dict] = []
        for node in self.ordered_questions():
            for binding in node.get("sets") or []:
                if isinstance(binding, dict) and binding.get("slot") == slot_id:
                    found.append(node)
                    break
        return found

    def provenance(self, node_id: str) -> dict:
        """The provenance envelope for a node, ready for citation."""
        node = (
            self.rules.get(node_id)
            or self.operators.get(node_id)
            or self.uncertainties.get(node_id)
            or self.sources.get(node_id)
            or self.guards.get(node_id)
            or self.branches.get(node_id)
            or self.annual.get(node_id)
        )
        if node is None:
            return {"node_id": node_id, "source_class": None, "confidence": None}
        return {
            "node_id": node_id,
            "source_class": node.get("source_class"),
            "authority": node.get("authority"),
            "instrument": node.get("instrument"),
            "article": node.get("article"),
            "effective_version": node.get("effective_version"),
            "effective_date": node.get("effective_date"),
            "confidence": node.get("confidence"),
            "derivation": node.get("derivation"),
            "sources": node.get("sources"),
            "last_validated": node.get("last_validated"),
            "next_revalidation": node.get("next_revalidation"),
        }

    def outgoing(self, node_id: str) -> list[dict[str, str]]:
        """Declared relations out of a node, as (edge, target) pairs."""
        node, cls = self._locate(node_id)
        if node is None:
            return []
        edges: list[dict[str, str]] = []
        for field, edge in EDGE_BY_FIELD.items():
            value = node.get(field)
            if value is None:
                continue
            targets = value if isinstance(value, list) else [value]
            for target in targets:
                if isinstance(target, str):
                    edges.append({"edge": edge, "field": field, "target": target})
        return edges

    def incoming(self, node_id: str) -> list[dict[str, str]]:
        edges: list[dict[str, str]] = []
        for cls, registry in self._registry_by_class.items():
            for source_id, node in registry.items():
                for field, edge in EDGE_BY_FIELD.items():
                    value = node.get(field)
                    if value is None:
                        continue
                    targets = value if isinstance(value, list) else [value]
                    if node_id in targets:
                        edges.append({"edge": edge, "field": field, "source": source_id, "source_class": cls})
        return edges

    def _locate(self, node_id: str) -> tuple[dict | None, str | None]:
        for cls, registry in self._registry_by_class.items():
            if node_id in registry:
                return registry[node_id], cls
        return None, None

    def node_class(self, node_id: str) -> str | None:
        return self._locate(node_id)[1]

    # ---------------------------------------------------- body authority chain

    def body_operator_scope(self) -> dict[str, list[str]]:
        """Body branches that list each operator. The graph listing is the scope."""
        scope: dict[str, list[str]] = {}
        for operator_id, operator in self.operators.items():
            if any(
                (self.branches.get(str(branch_id)) or {}).get("domain") == "BODY"
                for branch_id in operator.get("applies_to_branches") or []
            ):
                scope.setdefault(operator_id, [])
        for branch_id, branch in self.branches.items():
            if branch.get("domain") != "BODY":
                continue
            for operator_id in branch.get("operators") or []:
                scope.setdefault(str(operator_id), []).append(branch_id)
        return {operator_id: sorted(branches) for operator_id, branches in scope.items()}

    def body_operator_authority_report(self) -> tuple[list[str], list[str]]:
        """Prove operator → rule → source → authority class → effective date → scope.

        Broken links are issues. Mirror tiers and missing reviewers are findings.
        Findings stay visible and are not rewritten into the source register.
        """
        issues: list[str] = []
        findings: list[str] = []
        for operator_id, branch_scope in self.body_operator_scope().items():
            operator = self.operators.get(operator_id)
            if operator is None:
                issues.append(
                    f"operator {operator_id}: listed on {branch_scope} but the operator node is missing"
                )
                continue
            issues.extend(self._body_operator_chain_issues(operator_id, operator, branch_scope))
            findings.extend(self._body_operator_chain_findings(operator_id, operator, branch_scope))
        return issues, _unique(findings)

    def _body_operator_chain_issues(
        self, operator_id: str, operator: dict, branch_scope: list[str]
    ) -> list[str]:
        issues: list[str] = []
        rule_ids = [str(item) for item in operator.get("sourced_from") or []]
        if not rule_ids:
            issues.append(f"operator {operator_id}: no rule in the authority chain")
            return issues
        if not branch_scope:
            issues.append(f"operator {operator_id}: no body branch scope")
        for rule_id in rule_ids:
            rule = self.rules.get(rule_id)
            if rule is None:
                issues.append(f"operator {operator_id}: rule {rule_id} is missing")
                continue
            if rule.get("source_class") in (None, ""):
                issues.append(f"operator {operator_id}: rule {rule_id} has no authority class")
            elif rule.get("source_class") not in self.source_class_rank:
                issues.append(
                    f"operator {operator_id}: rule {rule_id} has unknown authority class "
                    f"{rule.get('source_class')!r}"
                )
            if rule.get("authority") in (None, ""):
                issues.append(f"operator {operator_id}: rule {rule_id} has no authority")
            if rule.get("effective_date") in (None, ""):
                issues.append(f"operator {operator_id}: rule {rule_id} has no effective date")
            source_ids = [str(item) for item in rule.get("sources") or []]
            if not source_ids:
                issues.append(f"operator {operator_id}: rule {rule_id} has no source")
            for source_id in source_ids:
                if source_id not in self.sources:
                    issues.append(
                        f"operator {operator_id}: rule {rule_id} source {source_id} is missing"
                    )
        return issues

    def _body_operator_chain_findings(
        self, operator_id: str, operator: dict, branch_scope: list[str]
    ) -> list[str]:
        findings: list[str] = []
        declared = sorted(
            branch
            for branch in operator.get("applies_to_branches") or []
            if (self.branches.get(str(branch)) or {}).get("domain") == "BODY"
        )
        if declared != branch_scope:
            findings.append(
                f"operator {operator_id}: declared body scope {declared} differs from "
                f"listing scope {branch_scope}; the declared scope is not rewritten"
            )
        for rule_id in [str(item) for item in operator.get("sourced_from") or []]:
            rule = self.rules.get(rule_id)
            if rule is None:
                continue
            for source_id in [str(item) for item in rule.get("sources") or []]:
                source = self.sources.get(source_id)
                if source is None:
                    continue
                tier = source.get("source_tier")
                if tier == "PRIMARY_MIRROR":
                    findings.append(
                        f"source {source_id}: source_tier PRIMARY_MIRROR is left unchanged"
                    )
                if not source.get("reviewer"):
                    findings.append(f"source {source_id}: reviewer is missing")
                note = str(source.get("access_note") or "").lower()
                if "timed out" in note or "not retrieved" in note:
                    findings.append(
                        f"source {source_id}: official host was not retrieved; "
                        f"tier {tier} is not reinterpreted"
                    )
        return findings

    # ------------------------------------------------------------ validation

    def validate(self) -> list[str]:
        """Integrity gate. An empty list means the graph is internally sound."""
        issues: list[str] = []

        for entry in self.ontology["source_class_hierarchy"]:
            if entry["id"] not in SOURCE_CLASSES:
                issues.append(f"ontology: unknown source_class {entry['id']!r}")
        ranks = [entry["rank"] for entry in self.ontology["source_class_hierarchy"]]
        if len(set(ranks)) != len(ranks):
            issues.append("ontology: duplicate source_class ranks")

        for node in self.rules.values():
            rule_id = node.get("node_id", "<missing id>")
            for field in REQUIRED_RULE_FIELDS:
                if node.get(field) in (None, ""):
                    issues.append(f"rule {rule_id}: missing provenance field {field!r}")
            confidence = node.get("confidence")
            if confidence is not None and not (0 <= float(confidence) <= 1):
                issues.append(f"rule {rule_id}: confidence {confidence} outside [0,1]")
            if node.get("source_class") not in self.source_class_rank:
                issues.append(f"rule {rule_id}: unknown source_class {node.get('source_class')!r}")
            if not node.get("sources"):
                issues.append(f"rule {rule_id}: no source reference")

        for node in self.operators.values():
            operator_id = node.get("node_id", "<missing id>")
            if node.get("type") not in OPERATOR_TYPES:
                issues.append(f"operator {operator_id}: unknown type {node.get('type')!r}")
            implementation = node.get("implementation")
            if implementation:
                try:
                    resolve_callable(implementation)
                except (ImportError, AttributeError) as exc:
                    issues.append(f"operator {operator_id}: implementation {implementation!r} -> {exc}")
            if not node.get("sourced_from"):
                issues.append(f"operator {operator_id}: no rule provenance")

        for node in self.branches.values():
            branch_id = node.get("branch", "<missing id>")
            if node.get("order_status") not in CONTROLLED_ORDER_STATUSES:
                issues.append(f"branch {branch_id}: unknown order_status {node.get('order_status')!r}")
            if node.get("order_status") == "UNRESOLVED" and not node.get("scenarios"):
                issues.append(f"branch {branch_id}: unresolved order with no scenarios")

        for node in self.uncertainties.values():
            uncertainty_id = node.get("node_id", "<missing id>")
            for field in REQUIRED_UNCERTAINTY_FIELDS:
                if node.get(field) is None:
                    issues.append(f"uncertainty {uncertainty_id}: missing {field!r}")
            if node.get("blocking") and not node.get("scenarios"):
                issues.append(f"uncertainty {uncertainty_id}: blocking but no candidate scenarios")

        for node in self.contradictions.values():
            contradiction_id = node.get("node_id", "<missing id>")
            if node.get("resolution") not in CONTRADICTION_RESOLUTIONS:
                issues.append(f"contradiction {contradiction_id}: unknown resolution {node.get('resolution')!r}")
            for field in ("candidate_source_class", "controlling_source_class"):
                if node.get(field) not in self.source_class_rank:
                    issues.append(f"contradiction {contradiction_id}: unknown {field} {node.get(field)!r}")
            candidate_rank = self.source_class_rank.get(node.get("candidate_source_class"))
            controlling_rank = self.source_class_rank.get(node.get("controlling_source_class"))
            if (
                candidate_rank is not None
                and controlling_rank is not None
                and candidate_rank < controlling_rank
                and node.get("resolution") == "REJECT_CANDIDATE"
            ):
                issues.append(
                    f"contradiction {contradiction_id}: rejects a higher-ranked source class"
                )

        for node in self.guards.values():
            guard_id = node.get("node_id", "<missing id>")
            enforced_in = node.get("enforced_in")
            if enforced_in:
                try:
                    resolve_callable(enforced_in)
                except (ImportError, AttributeError) as exc:
                    issues.append(f"guard {guard_id}: enforced_in {enforced_in!r} -> {exc}")
            if not node.get("triggered_label"):
                issues.append(f"guard {guard_id}: no triggered_label, so the guard is unobservable")

        for node in self.exclusions.values():
            exclusion_id = node.get("node_id", "<missing id>")
            if not node.get("cause_predicate"):
                issues.append(f"exclusion {exclusion_id}: empty cause_predicate")
            if node["type"] == "EXCLUDED_BUT_ENDORSABLE" and not node.get("restorable_by"):
                issues.append(f"exclusion {exclusion_id}: endorsable but not restorable")
            if node["type"] == "NON_COMPENSABLE" and node.get("restorable_by"):
                issues.append(f"exclusion {exclusion_id}: non-compensable yet restorable")

        # Referential integrity over declared reference fields.
        for cls, field, target_cls in RESOLVABLE_FIELDS:
            registry = self._registry_by_class[cls]
            for node_id, node in registry.items():
                value = node.get(field)
                if value is None:
                    continue
                targets = value if isinstance(value, list) else [value]
                for target in targets:
                    if not isinstance(target, str):
                        issues.append(f"{cls} {node_id}: {field} entry is not a string")
                        continue
                    if target_cls == "ANY":
                        if target not in self.all_ids:
                            issues.append(f"{cls} {node_id}: {field} -> unknown node {target!r}")
                        continue
                    if target not in self._registry_by_class[target_cls]:
                        issues.append(
                            f"{cls} {node_id}: {field} -> unknown {target_cls} {target!r}"
                        )

        for alias, mapping in self.branch_aliases.items():
            if mapping.get("branch") not in self.branches:
                issues.append(f"ontology: alias {alias} -> unknown branch {mapping.get('branch')!r}")

        issues.extend(self.superseded_reference_issues())
        issues.extend(self.validate_review())
        issues.extend(self.body_operator_authority_issues())

        for rel_path in self.ontology.get("node_files", {}):
            if not (self.root / rel_path).exists():
                issues.append(f"ontology: node_files entry {rel_path!r} does not exist")

        return issues

    def validate_review(self) -> list[str]:
        """Integrity gate for the review layer: stages, questions, slots, evidence, tiers.

        The point of this layer is that an intake form may only *select* knowledge
        that already exists, so the checks are mostly about reachability: a slot
        nothing supplies is a fabricated input, a predicate naming a node that does
        not exist is a rule that will silently never fire, and a tier citing a case
        that is not in the corpus is an unproven claim of completion.
        """
        issues: list[str] = []

        orders: dict[int, str] = {}
        for stage_id, node in self.stages.items():
            for field in ("order", "name", "closes_when", "gate"):
                if field == "order":
                    if not isinstance(node.get("order"), int):
                        issues.append(f"stage {stage_id}: missing or non-integer {field!r}")
                elif not node.get(field):
                    issues.append(f"stage {stage_id}: missing {field!r}")
            order = node.get("order")
            if isinstance(order, int):
                if order in orders:
                    issues.append(f"stage {stage_id}: order {order} shared with {orders[order]}")
                orders[order] = stage_id
            if not self.questions_for_stage(stage_id):
                issues.append(f"stage {stage_id}: no questions, so the stage can never be worked")

        for stage_id, node in self.stages.items():
            issues.extend(
                f"stage {stage_id}: {problem}" for problem in self._predicate_issues(node.get("gate"))
            )

        for question_id, node in self.questions.items():
            for field in ("stage", "order", "ask", "answer_format", "blocking", "tier"):
                if not node.get(field):
                    issues.append(f"question {question_id}: missing {field!r}")
            if node.get("answer_format") not in ANSWER_FORMATS:
                issues.append(
                    f"question {question_id}: unknown answer_format {node.get('answer_format')!r}"
                )
            if node.get("blocking") not in REVIEW_BLOCKING_LEVELS:
                issues.append(f"question {question_id}: unknown blocking {node.get('blocking')!r}")
            if node.get("tier") not in self.tiers:
                issues.append(f"question {question_id}: tier {node.get('tier')!r} is not a CaseTier")
            answers = [str(item) for item in node.get("answers") or []]
            if node.get("answer_format") in ("choice", "list_of_choices") and not answers:
                issues.append(f"question {question_id}: closed vocabulary expected, none declared")
            issues.extend(
                f"question {question_id}: {problem}"
                for problem in self._predicate_issues(node.get("when"))
            )
            for binding in node.get("sets") or []:
                if not isinstance(binding, dict):
                    issues.append(f"question {question_id}: binding is not an object")
                    continue
                slot_id = binding.get("slot")
                if slot_id not in self.slots:
                    issues.append(f"question {question_id}: sets unknown slot {slot_id!r}")
                    continue
                derive = binding.get("derive")
                if derive is not None and derive not in SLOT_DERIVATIONS:
                    issues.append(f"question {question_id}: unknown derive {derive!r}")
                when_answer = binding.get("when_answer")
                if "value" in binding and isinstance(binding["value"], (int, float)) and not isinstance(
                    binding["value"], bool
                ):
                    issues.append(
                        f"question {question_id}: binding literal {binding['value']!r} is an amount; "
                        "a questionnaire may select tokens, never supply numbers"
                    )
                if when_answer is not None:
                    wanted = [when_answer] if isinstance(when_answer, str) else list(when_answer)
                    for value in wanted:
                        if answers and str(value) not in answers:
                            issues.append(
                                f"question {question_id}: binding on {value!r} is not an "
                                f"admissible answer for {slot_id}"
                            )
            if node.get("sets") and not node.get("based_on") and not any(
                (self.slots.get(b.get("slot")) or {}).get("governed_by")
                for b in node["sets"]
                if isinstance(b, dict)
            ):
                issues.append(
                    f"question {question_id}: sets a parameter but names no authority "
                    "(neither based_on nor governed_by on the target slot)"
                )

        for slot_id, node in self.slots.items():
            for field in ("name", "case_field", "authority", "supplied_via", "missing_behavior"):
                if not node.get(field):
                    issues.append(f"slot {slot_id}: missing {field!r}")
            if node.get("authority") not in SLOT_AUTHORITIES:
                issues.append(f"slot {slot_id}: unknown authority {node.get('authority')!r}")
            if node.get("missing_behavior") not in MISSING_BEHAVIOURS:
                issues.append(
                    f"slot {slot_id}: unknown missing_behavior {node.get('missing_behavior')!r}"
                )
            for channel in node.get("supplied_via") or []:
                if channel not in SLOT_SUPPLY_CHANNELS:
                    issues.append(f"slot {slot_id}: unknown supply channel {channel!r}")
            subject_to = node.get("subject_to")
            if subject_to and not any(
                subject_to in (self.branches.get(branch) or {}).get("operators", [])
                for branch in node.get("required_for_branches") or []
            ):
                issues.append(
                    f"slot {slot_id}: names {subject_to} but no branch that requires the slot "
                    "composes that operator"
                )
            supplied = bool(self.questions_filling_slot(slot_id)) or any(
                slot_id in (tier.get("required_slots") or []) + (tier.get("conditional_slots") or [])
                for tier in self.tiers.values()
            )
            if not supplied:
                issues.append(
                    f"slot {slot_id}: nothing supplies it - no question binds it and no tier "
                    "requires it, so a value here could only be invented"
                )

        referenced_evidence: set[str] = set()
        for branch in self.branches.values():
            referenced_evidence.update(branch.get("required_evidence") or [])
        for node in self.questions.values():
            referenced_evidence.update(node.get("requires_evidence") or [])
        for item_id, node in self.evidence.items():
            if node.get("if_absent") not in ABSENT_BEHAVIOURS:
                issues.append(
                    f"evidence {item_id}: unknown if_absent {node.get('if_absent')!r}"
                )
            if node.get("if_absent") == "REDUCE_CONFIDENCE":
                raw = node.get("confidence_if_absent")
                try:
                    cap = D(raw)
                except (ValueError, ArithmeticError):
                    issues.append(
                        f"evidence {item_id}: REDUCE_CONFIDENCE requires a numeric "
                        "confidence_if_absent"
                    )
                else:
                    if cap < 0 or cap > 1:
                        issues.append(
                            f"evidence {item_id}: confidence_if_absent {raw} is outside 0..1"
                        )
            if node.get("source_class") not in self.source_class_rank:
                issues.append(f"evidence {item_id}: unknown source_class {node.get('source_class')!r}")
            issues.extend(
                f"evidence {item_id}: {problem}"
                for problem in self._predicate_issues(node.get("required_when"))
            )
            if item_id not in referenced_evidence:
                issues.append(
                    f"evidence {item_id}: no branch or question asks for it, so it is dead weight"
                )

        ranks: dict[int, str] = {}
        for tier_id, node in self.tiers.items():
            for field in ("rank", "name", "purpose", "gate", "permitted_outcomes"):
                if node.get(field) in (None, "", []):
                    issues.append(f"tier {tier_id}: missing {field!r}")
            rank = node.get("rank")
            if isinstance(rank, int):
                if rank in ranks:
                    issues.append(f"tier {tier_id}: rank {rank} shared with {ranks[rank]}")
                ranks[rank] = tier_id
            for outcome in node.get("permitted_outcomes") or []:
                if outcome not in OUTCOME_CLASSES:
                    issues.append(f"tier {tier_id}: unknown permitted outcome {outcome!r}")
            issues.extend(
                f"tier {tier_id}: {problem}" for problem in self._predicate_issues(node.get("gate"))
            )
            for case_id in node.get("example_cases") or []:
                if case_id not in self._fixture_ids():
                    issues.append(f"tier {tier_id}: example case {case_id!r} is not in the corpus")

        return issues

    def _fixture_ids(self) -> set[str]:
        if not hasattr(self, "_fixture_ids_cache"):
            path = self.root / "fixtures" / "cases.json"
            ids: set[str] = set()
            if path.exists():
                try:
                    payload = json.loads(path.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):  # pragma: no cover - reported below
                    payload = {}
                for entry in payload.get("cases", []):
                    if entry.get("id"):
                        ids.add(str(entry["id"]))
            self._fixture_ids_cache = ids
        return self._fixture_ids_cache

    # Every predicate key the review engine understands. A predicate naming a key
    # outside this set can never be evaluated, so it must fail validation instead
    # of quietly evaluating to False at runtime.
    PREDICATE_KEYS = (
        "always",
        "all",
        "any",
        "not",
        "answered",
        "unanswered",
        "answer_is",
        "slot_present",
        "slot_live",
        "branch_is",
        "stage_open",
        # Qualifiers that narrow slot_present; they never stand alone.
        "category",
        "value",
    )

    def _predicate_issues(self, predicate: Any, _depth: int = 0) -> list[str]:
        """Walk a gate/when predicate and check every id it names."""
        if not isinstance(predicate, dict):
            return []
        issues: list[str] = []
        unknown = [key for key in predicate if key not in self.PREDICATE_KEYS]
        if unknown:
            issues.append(f"unknown predicate key(s) {', '.join(sorted(unknown))}")
        for key in ("all", "any"):
            for child in predicate.get(key) or []:
                issues.extend(self._predicate_issues(child, _depth + 1))
        if "not" in predicate:
            issues.extend(self._predicate_issues(predicate["not"], _depth + 1))

        for question_id in self._as_ids(predicate.get("answered")):
            if question_id not in self.questions:
                issues.append(f"answered -> unknown question {question_id!r}")
        for question_id in self._as_ids(predicate.get("unanswered")):
            if question_id not in self.questions:
                issues.append(f"unanswered -> unknown question {question_id!r}")
        for question_id in self._as_ids(predicate.get("stage_open")):
            if question_id not in self.stages:
                issues.append(f"stage_open -> unknown stage {question_id!r}")

        answer_is = predicate.get("answer_is")
        if isinstance(answer_is, list) and answer_is:
            if answer_is[0] not in self.questions:
                issues.append(f"answer_is -> unknown question {answer_is[0]!r}")
            else:
                allowed = {str(item) for item in self.questions[answer_is[0]].get("answers") or []}
                for value in self._as_ids(answer_is[1:]):
                    if allowed and value not in allowed:
                        issues.append(
                            f"answer_is: {value!r} is not an admissible answer for {answer_is[0]}"
                        )
        elif answer_is is not None and not isinstance(answer_is, list):
            issues.append("answer_is must be [question_id, value...]")

        for slot_id in self._as_ids(predicate.get("slot_present")):
            if slot_id not in self.slots:
                issues.append(f"slot_present -> unknown slot {slot_id!r}")
        for uncertainty_id in self._as_ids(predicate.get("slot_live")):
            if uncertainty_id not in self.uncertainties:
                issues.append(f"slot_live -> unknown uncertainty {uncertainty_id!r}")
        for branch_id in self._as_ids(predicate.get("branch_is")):
            if self.canonical_branch(branch_id) not in self.branches:
                issues.append(f"branch_is -> unknown branch {branch_id!r}")
        return issues

    @staticmethod
    def _as_ids(value: Any) -> list[str]:
        if value is None:
            return []
        items = value if isinstance(value, list) else [value]
        return [str(item) for item in items if isinstance(item, (str, int))]

    def superseded_reference_issues(self) -> list[str]:
        """References that still point at a superseded rule.

        Ingesting a superseding rule marks the old node SUPERSEDED but does not
        silently rewire the graph: an operator or branch that still cites the old
        rule must be migrated by a human. Until that happens the graph is
        knowingly inconsistent, and validation says so rather than pretending the
        migration completed.
        """
        superseded = {
            rule_id: rule
            for rule_id, rule in self.rules.items()
            if rule.get("status") == "SUPERSEDED"
        }
        if not superseded:
            return []

        issues: list[str] = []

        def _replacement(rule_id: str) -> str:
            return superseded[rule_id].get("superseded_by") or "?"

        for branch_id, branch in self.branches.items():
            references = list(branch.get("governed_by") or [])
            references += list(branch.get("controlled_by") or [])
            if branch.get("base_rule"):
                references.append(branch["base_rule"])
            for reference in references:
                if reference in superseded:
                    issues.append(
                        f"branch {branch_id} still cites superseded rule {reference} "
                        f"(superseded by {_replacement(reference)})"
                    )

        for operator_id, operator in self.operators.items():
            for reference in operator.get("sourced_from") or []:
                if reference in superseded:
                    issues.append(
                        f"operator {operator_id} still cites superseded rule {reference} "
                        f"(superseded by {_replacement(reference)})"
                    )

        for rule_id, rule in self.rules.items():
            for reference in rule.get("derived_from") or []:
                if reference in superseded:
                    issues.append(
                        f"rule {rule_id} still derives from superseded rule {reference} "
                        f"(superseded by {_replacement(reference)})"
                    )

        return issues
