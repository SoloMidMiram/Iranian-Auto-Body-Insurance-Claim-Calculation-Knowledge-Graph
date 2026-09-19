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

    def contradictions_by_topic(self, topic: str) -> list[dict]:
        return [c for c in self.contradictions.values() if c.get("topic") == topic]

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

        for rel_path in self.ontology.get("node_files", {}):
            if not (self.root / rel_path).exists():
                issues.append(f"ontology: node_files entry {rel_path!r} does not exist")

        return issues

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
