"""Knowledge graph integrity, provenance completeness and the contradiction matrix."""

from __future__ import annotations

import re
from decimal import Decimal

from iran_auto_claim.knowledge import OPERATOR_TYPES, SOURCE_CLASSES, resolve_callable

DATE = re.compile(r"^\d{4}[/-]\d{2}[/-]\d{2}$")


def test_graph_validates_clean(kb):
    assert kb.validate() == []


def test_every_rule_carries_a_complete_provenance_envelope(kb):
    for rule_id, rule in kb.rules.items():
        envelope = kb.provenance(rule_id)
        for field in (
            "source_class",
            "authority",
            "instrument",
            "article",
            "effective_version",
            "effective_date",
            "confidence",
        ):
            assert envelope[field] not in (None, ""), f"{rule_id} missing {field}"
        assert envelope["source_class"] in SOURCE_CLASSES
        assert 0 <= float(envelope["confidence"]) <= 1


def test_every_rule_states_whether_it_is_primary_text_or_derived(kb):
    for rule_id, rule in kb.rules.items():
        derivation = rule.get("derivation", "PRIMARY_TEXT")
        assert derivation in ("PRIMARY_TEXT", "IMPLEMENTATION_INFERENCE", "IMPLEMENTATION_INTERPRETATION")
        if derivation != "PRIMARY_TEXT":
            assert rule.get("derived_from"), f"{rule_id} is derived but cites no source rules"


def test_validation_dates_are_well_formed_and_in_the_future(kb):
    for rule_id, rule in kb.rules.items():
        assert DATE.match(rule["last_validated"]), rule_id
        assert DATE.match(rule["next_revalidation"]), rule_id
        assert rule["next_revalidation"] > rule["last_validated"], rule_id


def test_every_operator_family_is_registered(kb):
    registered = {node["type"] for node in kb.operators.values()}
    assert registered == set(OPERATOR_TYPES)


def test_operator_implementations_resolve(kb):
    for operator_id, node in kb.operators.items():
        implementation = node.get("implementation")
        if implementation:
            assert callable(resolve_callable(implementation)), operator_id


def test_every_blocking_uncertainty_is_reachable_from_a_branch(kb):
    referenced = set()
    for branch in kb.branches.values():
        referenced.update(branch.get("blocking_uncertainties") or [])
    for node in kb.blocking_uncertainties():
        assert node["node_id"] in referenced, (
            f"{node['node_id']} is blocking but no branch declares it, so it can never surface"
        )


def test_every_uncertainty_states_a_resolution_artefact(kb):
    for uncertainty_id, node in kb.uncertainties.items():
        assert node.get("resolution_artefact"), uncertainty_id
        assert node.get("engine_status"), uncertainty_id


def test_controlling_authority_outranks_the_rejected_candidate(kb):
    for node in kb.contradictions.values():
        candidate = kb.source_class_rank[node["candidate_source_class"]]
        controlling = kb.source_class_rank[node["controlling_source_class"]]
        assert controlling <= candidate, (
            f"{node['node_id']}: a lower-ranked source cannot control a higher-ranked one"
        )


def test_article10_is_modelled_as_a_ratio_not_a_deduction(kb):
    operator = kb.operator("OP_UNDERINSURANCE_RATIO")
    assert operator is not None
    assert "ARTICLE_10" in operator["aliases"]
    assert operator["type"] == "UNDERINSURANCE_RATIO"
    assert "min(1" in operator["formula"]
    rule = kb.rule("ALIAS_ARTICLE10_IS_UNDERINSURANCE_RATIO")
    assert rule["rule_payload"]["rejected_interpretation"] == "article_10_as_a_fixed_deduction"
    assert kb.contradictions["C01_ARTICLE10_DEDUCTION_VS_RATIO"]["resolution"] == "REJECT_CANDIDATE"


def test_annual_parameters_are_derived_from_the_bodily_ceiling(kb):
    diyah = kb.annual_value(1405, "DIYAH")
    threshold = kb.annual_value(1405, "CONVENTIONAL_THRESHOLD")
    minimum = kb.annual_value(1405, "MIN_FINANCIAL")
    assert diyah == Decimal(28_000_000_000)
    assert threshold == Decimal(14_000_000_000)
    assert minimum == Decimal(700_000_000)
    assert threshold == diyah * Decimal("0.5")
    assert minimum == diyah * Decimal("0.025")
    for name in ("DIYAH", "CONVENTIONAL_THRESHOLD", "MIN_FINANCIAL"):
        node = kb.annual_parameter(1405, name)
        assert node["requires_primary_revalidation"] is True
        assert node["confidence"] < 0.9, "unverified annual data must not carry high confidence"


def test_unresolved_branches_offer_scenarios_and_resolved_ones_do_not(kb):
    for branch_id, branch in kb.branches.items():
        if branch["order_status"] == "UNRESOLVED":
            assert branch.get("scenarios"), branch_id
        if branch["order_status"] == "RESOLVED":
            assert not branch.get("scenarios"), f"{branch_id} is resolved yet still offers scenarios"


def test_total_loss_threshold_is_strictly_greater_than(kb):
    rule = kb.rule("REG53_ART19_TOTAL_LOSS_THRESHOLD")
    assert rule["rule_payload"]["comparison"] == "STRICTLY_GREATER_THAN"
    assert rule["rule_payload"]["exactly_at_threshold_is_total_loss"] is False
    assert kb.contradictions["C06_TOTAL_LOSS_THRESHOLD_75_INCLUSIVE"]["resolution"] == "REJECT_CANDIDATE"


def test_article8_whole_car_ratio_is_rejected_and_has_a_guardrail(kb):
    contradiction = kb.contradictions["C09_ARTICLE8_WHOLE_CAR_RATIO"]
    assert contradiction["resolution"] == "REJECT_CANDIDATE"
    assert "G_ARTICLE8_NO_WHOLE_CAR_RATIO" == contradiction["guardrail"]
    guard = kb.guards["G_ARTICLE8_NO_WHOLE_CAR_RATIO"]
    assert callable(resolve_callable(guard["enforced_in"]))


def test_depreciation_rule_is_not_consumables_only(kb):
    rule = kb.rule("REG53_ART19_REPLACEMENT_PART_DEPRECIATION")
    assert rule["rule_payload"]["scope"] == "all_replaced_parts"
    assert rule["rule_payload"]["scope_is_consumables_only"] is False
    assert rule["rule_payload"]["excluded_part_categories"] == ["GLASS", "LAMP_GLASS"]
    assert rule["rule_payload"]["annual_rate"] == 0.05
    assert rule["rule_payload"]["maximum_rate"] == 0.25


def test_no_rule_or_operator_claims_a_universal_glass_franchise(kb):
    franchise = kb.rule("REG53_POLICY_DEFINED_FRANCHISE")
    assert franchise["rule_payload"]["statutory_universal_rate"] is None
    assert franchise["rule_payload"]["universal_glass_rate"] is None
    assert kb.contradictions["C04_UNIVERSAL_GLASS_FRANCHISE_20"]["resolution"] == "REJECT_CANDIDATE"


def test_every_guardrail_is_executable_and_observable(kb):
    for guard_id, guard in kb.guards.items():
        assert callable(resolve_callable(guard["enforced_in"])), guard_id
        assert guard.get("triggered_label"), guard_id
        assert guard.get("violation_status"), guard_id


def test_every_exclusion_is_one_of_the_two_states(kb):
    for exclusion_id, exclusion in kb.exclusions.items():
        assert exclusion["type"] in ("EXCLUDED_BUT_ENDORSABLE", "NON_COMPENSABLE"), exclusion_id
        assert exclusion.get("uninsured_outcome", {}).get("reason"), exclusion_id


def test_graph_edges_are_declared_in_the_ontology(kb):
    declared = {edge["id"] for edge in kb.ontology["edges"]}
    for node_id in kb.all_ids:
        for edge in kb.outgoing(node_id):
            assert edge["edge"] in declared, f"{node_id} uses undeclared edge {edge['edge']}"


def test_branch_aliases_map_onto_real_branches(kb):
    for alias, mapping in kb.branch_aliases.items():
        assert mapping["branch"] in kb.branches, alias


def test_source_class_ranks_are_ordered_and_unique(kb):
    ranks = sorted(kb.source_class_rank.values())
    assert ranks == list(range(1, len(ranks) + 1))
    assert kb.source_class_rank["STATUTE"] < kb.source_class_rank["REGULATION"]
    assert kb.source_class_rank["REGULATION"] < kb.source_class_rank["CIRCULAR"]
    assert kb.source_class_rank["CIRCULAR"] < kb.source_class_rank["POLICY"]
    assert kb.source_class_rank["POLICY"] < kb.source_class_rank["INSURER_PROCEDURE"]
    assert kb.source_class_rank["INSURER_PROCEDURE"] < kb.source_class_rank["EDUCATIONAL"]
