"""Command line interface.

    python claim.py fixtures
    python claim.py validate
    python claim.py calc cases/example_partial.json
    python claim.py json cases/example_partial.json
    python claim.py classify cases/example_partial.json
    python claim.py unknowns
    python claim.py contradictions --topic ARTICLE_8_CALCULATION
    python claim.py branch PARTIAL_DAMAGE
    python claim.py rule REG53_ART19_REPLACEMENT_PART_DEPRECIATION
    python claim.py node OP_UNDERINSURANCE_RATIO
    python claim.py params --year 1405
    python claim.py operators
    python claim.py sources
    python claim.py ingest submissions/new_rule.json [--write]
    python claim.py review cases/review_t1_fullcover_partial.json [--emit-case out.json] [--calc]
    python claim.py questionnaire [--stage S2_EVENT_CAUSATION] [--format markdown]
    python claim.py parameters [--branch PARTIAL_DAMAGE] [--format markdown]
    python claim.py ladder [--format markdown]
    python claim.py flowchart
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from . import money
from .case import Case
from .classify import classify
from .engine import compute
from .fixtures import run_all
from .ingest import apply_ingest, load_submission, plan_ingest
from .knowledge import DEFAULT_ROOT, Knowledge, Node
from .render import render_claim
from .schema_input import InputSchemaError, validate_claim
from .review import (
    Review,
    ReviewInputError,
    ladder_markdown,
    mermaid_architecture,
    mermaid_branch_tree,
    mermaid_flowchart,
    parameters_markdown,
    questionnaire_markdown,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="claim", description="Iranian motor claim rule engine")
    parser.add_argument("--root", default=str(DEFAULT_ROOT), help="repository root")
    parser.add_argument("--as-of", default=None, help="report the graph as of a date (informational)")

    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("fixtures", help="run the P01-L50 validation corpus")
    sub.add_parser("validate", help="validate knowledge graph integrity")

    for name, help_text in (
        ("calc", "calculate a claim and render the explanation"),
        ("json", "calculate a claim and print the machine result"),
        ("classify", "derive the branch for a case without calculating"),
    ):
        p = sub.add_parser(name, help=help_text)
        p.add_argument("case", help="path to a case JSON file")

    p = sub.add_parser("unknowns", help="list unresolved variables")
    p.add_argument("--all", action="store_true", help="include non-blocking uncertainties")

    p = sub.add_parser("contradictions", help="list the contradiction matrix")
    p.add_argument("--topic", default=None)

    p = sub.add_parser("branch", help="show a branch and its operator order")
    p.add_argument("branch")

    p = sub.add_parser("rule", help="show a rule and its provenance envelope")
    p.add_argument("rule_id")

    p = sub.add_parser("node", help="show any node and its graph edges")
    p.add_argument("node_id")

    p = sub.add_parser("params", help="show versioned annual parameters")
    p.add_argument("--year", type=int, default=None)

    sub.add_parser("operators", help="show the operator registry")
    sub.add_parser("sources", help="show the source register")
    sub.add_parser("queries", help="answer the documented graph query patterns from the graph")

    p = sub.add_parser("ingest", help="validate a new-rule submission (dry run by default)")
    p.add_argument("submission")
    p.add_argument("--write", action="store_true", help="commit the submission to the knowledge files")
    p.add_argument(
        "--accept-review",
        action="store_true",
        help="commit even though the submission contradicts existing rules (records the human decision)",
    )

    p = sub.add_parser("review", help="run the case-review questionnaire over an answers file")
    p.add_argument("answers", help="path to a review answers JSON file")
    p.add_argument("--json", action="store_true", help="print the machine-readable review")
    p.add_argument("--emit-case", default=None, metavar="PATH", help="write the derived claim case")
    p.add_argument("--calc", action="store_true", help="also run the engine when the file is ready")

    p = sub.add_parser("questionnaire", help="print the investigation procedure")
    p.add_argument("--stage", default=None, help="limit to one stage, e.g. S2_EVENT_CAUSATION")
    p.add_argument("--format", default="text", choices=("text", "markdown"))

    p = sub.add_parser("parameters", help="print the parameter-selection matrix")
    p.add_argument("--branch", default=None, help="limit to one branch")
    p.add_argument("--format", default="text", choices=("text", "markdown"))

    p = sub.add_parser("ladder", help="print the iterative completion tiers")
    p.add_argument("--format", default="text", choices=("text", "markdown"))

    sub.add_parser("flowchart", help="print the review-and-calculation flowchart as mermaid")

    return parser


def _print_schema_error(error: InputSchemaError) -> None:
    print(
        json.dumps(
            {"ok": False, "errors": [item.to_dict() for item in error.errors]},
            ensure_ascii=False,
            indent=2,
        )
    )


def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):  # pragma: no cover - platform dependent
        pass

    args = build_parser().parse_args(argv)
    kb = Knowledge.load(args.root)
    handler = _HANDLERS[args.command]
    try:
        return handler(args, kb)
    except InputSchemaError as error:
        _print_schema_error(error)
        return 1


def _load_case(path: str) -> Case:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if "claim_id" not in payload and "id" in payload:
        payload["claim_id"] = payload["id"]
    payload.setdefault("unit", "million_toman")
    validate_claim(payload)
    return Case(payload)


def _cmd_fixtures(args: argparse.Namespace, kb: Knowledge) -> int:
    report = run_all(kb)
    failures = 0
    for entry in report:
        if entry["ok"]:
            payable = money.fmt(entry["payable"], "million_toman")
            extra = ""
            if entry["payable_scenarios"]:
                extra = " scenarios=" + ",".join(
                    money.fmt(value, "million_toman") for value in entry["payable_scenarios"]
                )
            if entry["status"]:
                extra += f" status={entry['status']}"
            print(f"PASS {entry['id']:<5} {entry['branch']:<28} payable={payable}{extra}")
        else:
            failures += 1
            print(f"FAIL {entry['id']:<5} {entry['branch']}")
            for problem in entry["problems"]:
                print(f"       {problem}")
    print(f"\n{len(report) - failures}/{len(report)} fixtures passed")
    return 1 if failures else 0


def _cmd_validate(args: argparse.Namespace, kb: Knowledge) -> int:
    issues = kb.validate()
    if issues:
        print(f"{len(issues)} integrity issue(s):")
        for issue in issues:
            print(f"  - {issue}")
        return 1
    print("knowledge graph OK")
    print(f"  nodes: {len(kb.all_ids)}")
    for cls, registry in sorted(kb._registry_by_class.items()):
        print(f"    {cls:<16}{len(registry)}")
    print(f"  blocking uncertainties: {len(kb.blocking_uncertainties())}")
    print(f"  contradiction nodes: {len(kb.contradictions)}")
    return 0


def _cmd_calc(args: argparse.Namespace, kb: Knowledge) -> int:
    case = _load_case(args.case)
    result = compute(case, kb)
    print(render_claim(result, kb, case.unit))
    return 0


def _cmd_json(args: argparse.Namespace, kb: Knowledge) -> int:
    case = _load_case(args.case)
    result = compute(case, kb)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 0


def _cmd_classify(args: argparse.Namespace, kb: Knowledge) -> int:
    case = _load_case(args.case)
    verdict = classify(case, kb)
    if case.declared_branch:
        verdict["declared_branch"] = case.declared_branch
        verdict["note"] = (
            "the engine uses the declared branch and does not re-derive it; the derivation above is "
            "shown for comparison"
        )
    print(json.dumps(verdict, ensure_ascii=False, indent=2))
    return 0


def _cmd_unknowns(args: argparse.Namespace, kb: Knowledge) -> int:
    nodes = list(kb.uncertainties.values())
    if not args.all:
        nodes = [node for node in nodes if node.get("blocking")]
    nodes.sort(key=lambda node: (not node.get("blocking"), node["node_id"]))
    for node in nodes:
        marker = "BLOCKING " if node.get("blocking") else "advisory "
        print(f"{marker}{node['node_id']}")
        print(f"  question : {node.get('question')}")
        print(f"  status   : {node.get('engine_status')}")
        if node.get("config_field"):
            print(f"  carrier  : {node.get('config_field')}")
        for scenario in node.get("scenarios") or []:
            print(f"  scenario : {scenario}")
        print(f"  resolves : {node.get('resolution_artefact')}")
        print()
    print(f"{len(nodes)} unresolved variable(s) shown")
    return 0


def _cmd_contradictions(args: argparse.Namespace, kb: Knowledge) -> int:
    nodes = sorted(kb.contradictions.values(), key=lambda node: node["node_id"])
    if args.topic:
        nodes = [node for node in nodes if node.get("topic") == args.topic]
    for node in nodes:
        print(f"{node['node_id']}  [{node.get('topic')}]")
        print(f"  candidate   : {node.get('candidate_rule')} ({node.get('candidate_source_class')})")
        print(f"  controlling : {node.get('controlling_rule')} ({node.get('controlling_source_class')})")
        print(f"  resolution  : {node.get('resolution')}  confidence={node.get('confidence')}")
        print(f"  engine uses : {node.get('engine_uses')}")
        print(f"  why         : {node.get('explanation')}")
        print()
    print(f"{len(nodes)} contradiction node(s)")
    return 0


def _cmd_branch(args: argparse.Namespace, kb: Knowledge) -> int:
    info = kb.branch(args.branch)
    if info is None:
        print(f"unknown branch {args.branch!r}")
        return 1
    print(f"{info['branch']}  domain={info.get('domain')}")
    if info.get("base_rule"):
        print(f"  base rule   : {info['base_rule']}")
    if info.get("base_expression"):
        print(f"  base        : {info['base_expression']}")
    print(f"  order status: {info.get('order_status')}")
    print(f"  reason      : {info.get('order_status_reason')}")
    print("  operator order:")
    for operator_id in info.get("operators", []):
        operator = kb.operator(operator_id)
        status = operator.get("status") if operator else "MISSING"
        print(f"    - {operator_id:<44}{status}")
    for scenario in info.get("scenarios") or []:
        print(f"  scenario {scenario.get('scenario_id')}: {scenario.get('name')}")
        print(f"    {scenario.get('expression')}")
    print("  governed by:")
    for rule_id in info.get("governed_by", []):
        rule = kb.rule(rule_id)
        if rule:
            print(f"    - {rule_id} (Art. {rule.get('article')}, conf {rule.get('confidence')})")
    for uncertainty_id in info.get("blocking_uncertainties") or []:
        node = kb.uncertainty(uncertainty_id)
        print(f"  blocking uncertainty: {uncertainty_id} - {(node or {}).get('question')}")
    for guard_id in info.get("guardrails") or []:
        print(f"  guardrail: {guard_id}")
    return 0


def _cmd_rule(args: argparse.Namespace, kb: Knowledge) -> int:
    rule = kb.rule(args.rule_id)
    if rule is None:
        print(f"unknown rule {args.rule_id!r}")
        return 1
    envelope = kb.provenance(args.rule_id)
    print(f"{envelope['node_id']}  [{envelope['source_class']}]")
    print(f"  authority   : {envelope['authority']}")
    print(f"  instrument  : {envelope['instrument']} Art. {envelope['article']}")
    print(f"  version     : {envelope['effective_version']} (effective {envelope['effective_date']})")
    print(f"  confidence  : {envelope['confidence']}")
    print(f"  derivation  : {envelope['derivation'] or 'PRIMARY_TEXT'}")
    if rule.get("derived_from"):
        print(f"  derived from: {', '.join(rule['derived_from'])}")
    print(f"  validated   : {envelope['last_validated']} (next {envelope['next_revalidation']})")
    print(f"  branches    : {', '.join(rule.get('applies_to_branches') or [])}")
    if rule.get("article_number_certainty"):
        print(f"  article ref : {rule['article_number_certainty']}")
    print("  payload:")
    print(json.dumps(rule.get("rule_payload"), ensure_ascii=False, indent=4))
    print("  sources:")
    for source_id in rule.get("sources", []):
        source = kb.source(source_id)
        title = source.get("title") if source else "MISSING from the register"
        print(f"    - {source_id}: {title}")
    print("  cited by:")
    for edge in kb.incoming(args.rule_id):
        print(f"    - {edge['source']} ({edge['source_class']}) via {edge['edge']}")
    return 0


def _cmd_node(args: argparse.Namespace, kb: Knowledge) -> int:
    node = Node.of(kb, args.node_id)
    if node is None:
        print(f"unknown node {args.node_id!r}")
        return 1
    print(f"{args.node_id}  [{node.cls}]")
    print(json.dumps(node.data, ensure_ascii=False, indent=2))
    print("outgoing edges:")
    for edge in kb.outgoing(args.node_id):
        print(f"  --{edge['edge']}--> {edge['target']}")
    print("incoming edges:")
    for edge in kb.incoming(args.node_id):
        print(f"  <--{edge['edge']}-- {edge['source']} ({edge['source_class']})")
    return 0


def _cmd_params(args: argparse.Namespace, kb: Knowledge) -> int:
    for node in sorted(kb.annual.values(), key=lambda item: (item["year"], item["name"])):
        if args.year and int(node["year"]) != args.year:
            continue
        print(f"{node['node_id']}  {node['year']}  {node['name']}")
        print(f"  value      : {int(node['value']):,} {node.get('currency')} (IRR)")
        print(f"  display    : {node.get('value_toman_display'):,} toman")
        print(f"  source tier: {node.get('source_tier')}  confidence={node.get('confidence')}")
        if node.get("derivation"):
            print(f"  derivation : {node['derivation']} (from {node.get('derived_from')})")
        if node.get("requires_primary_revalidation"):
            print("  WARNING    : requires primary revalidation before certification")
        print(f"  used by    : {', '.join(node.get('used_by') or [])}")
        print()
    for entry in kb.annual_raw.get("pending_years", []):
        if args.year and int(entry["year"]) != args.year:
            continue
        print(f"{entry['year']}  {entry.get('status')} - {entry.get('action')}")
    return 0


def _cmd_queries(args: argparse.Namespace, kb: Knowledge) -> int:
    """Answer the report's documented knowledge-graph query patterns from the graph."""
    from .operators import replacement_part_depreciation_rate

    print("HOW IS PARTIAL DAMAGE CALCULATED?")
    branch = kb.branch("PARTIAL_DAMAGE")
    print(f"  Branch({branch['branch']}) -> composes -> Operator[] -> ordered_by -> OperatorOrder")
    print(f"  order status: {branch['order_status']}  ({branch['order_status_reason']})")
    for scenario in branch.get("scenarios") or []:
        print(f"  scenario {scenario['scenario_id']}: {scenario['expression']}")
    print("  rules:")
    for rule in kb.rules_for_branch("PARTIAL_DAMAGE"):
        print(f"    - {rule['node_id']} (Art. {rule['article']}, conf {rule['confidence']})")
    print()

    print("WHAT IS THE DEPRECIATION RATE FOR AN 8-YEAR-OLD CAR?")
    for production_year, note in (
        (1398, "8th production-year index -> mid schedule"),
        (1396, "10th production-year index -> at the 25% ceiling"),
        (1403, "3rd production-year index -> before depreciation begins"),
    ):
        rate = replacement_part_depreciation_rate(production_year, 1405, "OTHER_REPLACEMENT_PART")
        print(f"  production {production_year}, claim 1405: rate={rate}  ({note})")
    glass_rate = replacement_part_depreciation_rate(1396, 1405, "GLASS")
    print(f"  same 10th-index car, GLASS part: rate={glass_rate}  (expressly exempt)")
    print("  see operator OP_DEPRECIATION_REPLACEMENT_PART for the formula and provenance")
    print()

    print("IS GLASS DEPRECIATED?")
    operator = kb.operator("OP_DEPRECIATION_REPLACEMENT_PART")
    rule = kb.rule("REG53_ART19_GLASS_DEPRECIATION_EXEMPTION")
    print(f"  DamageComponent(GLASS) -> subject_to -> {operator['node_id']}? NO")
    print(f"  exempt categories: {', '.join(rule['rule_payload']['exempt_categories'])}")
    print(f"  {rule['node_id']}: {rule['rule_payload']['note']}")
    print(f"  operator scope: {operator['scope']}")
    print()

    print("WHAT IS ARTICLE 8?")
    rule = kb.rule("HIC_ARTICLE8_CORRESPONDING_DAMAGE")
    print(f"  {rule['node_id']} ({rule['source_class']}, {rule['effective_version']})")
    for key, value in rule["rule_payload"].items():
        print(f"    {key}: {value}")
    for contradiction in kb.contradictions_by_topic("ARTICLE_8_CALCULATION"):
        print(f"  contradiction {contradiction['node_id']}: {contradiction['resolution']}")
        print(f"    rejected: {contradiction['candidate_rule']}")
    print()

    print("WHY DID A CLAIM GET THIS AMOUNT?")
    print("  Claim -> rule_trace -> [LegalRule, Operator, OperatorOrder, Confidence]")
    print("  run `claim.py calc <case.json>` to render the trace for a real case")
    trace_rules = kb.rules_for_branch("TOTAL_LOSS")
    print(f"  a TOTAL_LOSS trace can cite: {len(trace_rules)} rules")
    print()

    print("WHAT IS UNRESOLVED?")
    for node in kb.blocking_uncertainties():
        print(f"  {node['node_id']}  (blocks {', '.join(node.get('blocks') or []) or 'n/a'})")
        print(f"    {node['question']}")
    print()
    return 0


def _cmd_operators(args: argparse.Namespace, kb: Knowledge) -> int:
    for node in sorted(kb.operators.values(), key=lambda item: item["node_id"]):
        print(f"{node['node_id']}  [{node['type']}]")
        print(f"  formula : {node.get('formula')}")
        print(f"  status  : {node.get('status')}")
        print(f"  conf    : {node.get('confidence')}   configured by: {node.get('configured_by')}")
        print(f"  rules   : {', '.join(node.get('sourced_from') or [])}")
        implementation = node.get("implementation")
        if implementation:
            print(f"  impl    : {implementation}")
        elif node.get("implementation_note"):
            print(f"  impl    : none - {node['implementation_note']}")
        print()
    return 0


def _cmd_sources(args: argparse.Namespace, kb: Knowledge) -> int:
    for node in kb.sources.values():
        print(f"{node['node_id']}  [{node.get('source_class')}] tier={node.get('source_tier')}")
        print(f"  {node.get('title')}")
        print(f"  {node.get('url')}")
        if node.get("access_note"):
            print(f"  note: {node['access_note']}")
        print()
    return 0


def _cmd_ingest(args: argparse.Namespace, kb: Knowledge) -> int:
    submission = load_submission(args.submission)
    if args.write:
        try:
            written = apply_ingest(submission, kb, allow_review=args.accept_review)
        except ValueError as error:
            print(str(error))
            return 1
        print(json.dumps(written, ensure_ascii=False, indent=2))
        return 0
    plan = plan_ingest(submission, kb)
    print(json.dumps(plan, ensure_ascii=False, indent=2))
    print("\n(dry run: pass --write to commit)")
    return 0 if plan["ok"] else 1


def _cmd_review(args: argparse.Namespace, kb: Knowledge) -> int:
    try:
        review = Review.from_file(args.answers, kb)
    except ReviewInputError as error:
        print(f"review refused: {error}")
        return 1

    if args.emit_case:
        payload = review.case_payload()
        validate_claim(payload)
        Path(args.emit_case).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        print(f"wrote derived case to {args.emit_case}")

    if args.json:
        document = review.to_json()
        if not args.calc:
            document["calculation"] = None
        print(json.dumps(document, ensure_ascii=False, indent=2, default=str))
        return 0

    print(review.report())
    if args.calc and review.classification().get("branch"):
        result = review.calculate()
        if result is not None:
            print()
            print(render_claim(result, kb, review.unit))
    return 0


def _cmd_questionnaire(args: argparse.Namespace, kb: Knowledge) -> int:
    if args.format == "markdown" and not args.stage:
        print(questionnaire_markdown(kb))
        return 0

    stages = [args.stage] if args.stage else [s["node_id"] for s in kb.ordered_stages()]
    for stage_id in stages:
        stage = kb.stage(stage_id)
        if stage is None:
            print(f"unknown stage {stage_id!r}")
            return 1
        if args.format == "markdown":
            print(f"### {stage['node_id']} - {stage['name']}")
            print(f"*Closes when:* {stage['closes_when']}")
            print()
            print("| # | Ask | Admissible answers | Binds | Evidence | Blocking | Rung |")
            print("|---|---|---|---|---|---|---|")
        else:
            print(f"{stage['node_id']}  {stage['name']}")
            print(f"  closes when: {stage['closes_when']}")
            print(f"  why this gate: {stage['gate']}")
        for question in kb.questions_for_stage(stage_id):
            bindings = ", ".join(
                str(binding.get("slot"))
                for binding in question.get("sets") or []
                if isinstance(binding, dict)
            ) or "-"
            evidence = ", ".join(str(item) for item in question.get("requires_evidence") or []) or "-"
            answers = ", ".join(str(item) for item in question.get("answers") or []) or question.get(
                "answer_format", ""
            )
            when = ""
            if question.get("when"):
                when = f" [asked when: {json.dumps(question['when'], ensure_ascii=False)}]"
            if args.format == "markdown":
                print(
                    f"| {question['node_id']} | {question['ask']}{when} | {answers} | {bindings} | "
                    f"{evidence} | {question['blocking']} | {question['tier']} |"
                )
            else:
                print(f"  {question['node_id']}  ({question['blocking']}, rung {question['tier']})")
                print(f"      ask      : {question['ask']}{when}")
                if question.get("ask_fa"):
                    print(f"      ask_fa   : {question['ask_fa']}")
                print(f"      answers  : {answers}")
                print(f"      binds    : {bindings}")
                print(f"      evidence : {evidence}")
                if question.get("based_on"):
                    print(f"      because  : {question['based_on']}")
                for uncertainty_id in question.get("escalates_to") or []:
                    print(f"      surfaces : {uncertainty_id}")
                print(f"      why      : {question['why']}")
        if args.format == "markdown":
            print()
    return 0


def _cmd_parameters(args: argparse.Namespace, kb: Knowledge) -> int:
    if args.format == "markdown" and not args.branch:
        print(parameters_markdown(kb))
        return 0
    nodes = sorted(kb.slots.values(), key=lambda node: node["node_id"])
    if args.branch:
        wanted = kb.canonical_branch(args.branch)
        nodes = [node for node in nodes if wanted in (node.get("required_for_branches") or [])]
        if not nodes:
            print(f"no parameter slot is declared required for branch {args.branch!r}")
            return 1
    for node in nodes:
        fillers = [q["node_id"] for q in kb.questions_filling_slot(node["node_id"])]
        if args.format == "markdown":
            print(
                f"| {node['node_id']} | {node.get('unit')} | {node.get('authority')} | "
                f"{', '.join(fillers) or '-'} | {node.get('missing_behavior')} | "
                f"{node.get('blocking_uncertainty') or '-'} | {node.get('guardrail') or '-'} | "
                f"{', '.join(node.get('required_for_branches') or []) or '-'} |"
            )
            continue
        print(f"{node['node_id']}  [{node.get('authority')}]  unit={node.get('unit')}")
        print(f"  case field : {node.get('case_field')}")
        print(f"  supplied by: {', '.join(fillers) or '-'}  via {', '.join(node.get('supplied_via') or [])}")
        print(f"  if absent  : {node.get('missing_behavior')}")
        if node.get("governed_by"):
            print(f"  governed by: {node['governed_by']}")
        if node.get("subject_to"):
            print(f"  read by    : {node['subject_to']}")
        if node.get("blocking_uncertainty"):
            print(f"  blocks on  : {node['blocking_uncertainty']}")
        if node.get("guardrail"):
            print(f"  guarded by : {node['guardrail']}")
        print(f"  how to pick: {node.get('select')}")
        print()
    if args.format == "markdown" and args.branch:
        pass
    return 0


def _cmd_ladder(args: argparse.Namespace, kb: Knowledge) -> int:
    if args.format == "markdown":
        print(ladder_markdown(kb))
        return 0
    for node in kb.ordered_tiers():
        print(f"{node['node_id']}  {node['name']}")
        print(f"  adds        : {node.get('purpose')}")
        print(f"  gate        : {json.dumps(node.get('gate'), ensure_ascii=False)}")
        print(f"  branches    : {', '.join(node.get('reachable_branches') or [])}")
        print(f"  outcomes    : {', '.join(node.get('permitted_outcomes') or [])}")
        print(f"  slots       : {', '.join(node.get('required_slots') or []) or '-'}")
        for boundary in node.get("boundary_cases_required") or []:
            print(f"  boundary    : {boundary}")
        print(f"  corpus      : {', '.join(node.get('example_cases') or []) or '-'}")
        if node.get("exit_evidence"):
            print(f"  exit proof  : {node['exit_evidence']}")
        if node.get("must_not"):
            print(f"  must not    : {node['must_not']}")
        print(f"  calibration : {', '.join(node.get('calibration_needed') or []) or 'nothing outstanding'}")
        print(f"  next        : {node.get('next_tier') or 'end of ladder'}")
        print()
    for rule in kb.tiers_raw.get("promotion_rule", []):
        print(f"* {rule}")
    return 0


def _cmd_flowchart(args: argparse.Namespace, kb: Knowledge) -> int:
    print(mermaid_flowchart(kb))
    print()
    print(mermaid_architecture(kb))
    print()
    print(mermaid_branch_tree(kb))
    return 0


_HANDLERS: dict[str, Any] = {
    "fixtures": _cmd_fixtures,
    "validate": _cmd_validate,
    "calc": _cmd_calc,
    "json": _cmd_json,
    "classify": _cmd_classify,
    "unknowns": _cmd_unknowns,
    "contradictions": _cmd_contradictions,
    "branch": _cmd_branch,
    "rule": _cmd_rule,
    "node": _cmd_node,
    "params": _cmd_params,
    "operators": _cmd_operators,
    "sources": _cmd_sources,
    "queries": _cmd_queries,
    "ingest": _cmd_ingest,
    "review": _cmd_review,
    "questionnaire": _cmd_questionnaire,
    "parameters": _cmd_parameters,
    "ladder": _cmd_ladder,
    "flowchart": _cmd_flowchart,
}


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
