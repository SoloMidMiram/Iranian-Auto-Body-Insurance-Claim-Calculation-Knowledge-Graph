"""Response rendering: the report's Layer-4 output template.

This is a renderer, not the chatbot. It turns a CalcResult into the response
shape the report specifies: classification, applicable rules with citations,
the calculation, an explicit status, an escalation prompt when uncertainty is
live, and a source list. Keeping it separate from the engine means the engine
can be embedded in any interface without dragging explanation strings along.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from . import money
from .engine import CalcResult
from .knowledge import Knowledge

CALCULATION_ORDER = (
    ("assessed_gross", "Assessed gross damage"),
    ("gross_eligible", "Gross eligible (after part caps)"),
    ("depreciation", "Depreciation"),
    ("after_depreciation", "After depreciation"),
    ("article10_ratio", "Underinsurance ratio (قاعده نسبی / Article 10)"),
    ("franchise", "Franchise"),
    ("allowable_rescue_transport", "Allowable rescue / transport"),
    ("settlement_base", "Settlement base: min(market, insured)"),
    ("salvage_deduction", "Probable salvage deducted"),
    ("base_after_salvage", "Base after salvage"),
    ("corresponding_damage", "Corresponding damage (Article 8)"),
    ("insurer_payable", "Insurer payable"),
    ("non_corresponding_excess", "Non-corresponding excess"),
    ("remaining_inside_article8_cap", "Remaining inside the Article 8 cap"),
    ("own_body_excess_candidate", "Own-body-insurance candidate for the excess"),
    ("insurer_subrogation_ceiling", "Insurer subrogation ceiling"),
)

NON_MONEY_INLINE = {
    "article10_ratio",
    "threshold_ratio",
    "depreciation_source",
    "order_used",
    "vehicle_class",
    "salvage_disposition",
    "property_type",
    "article8_vehicle_cap",
    "exclusion_applied",
    "exclusion_state",
}


def render_claim(result: CalcResult, kb: Knowledge, unit: str | None = None) -> str:
    unit = unit or result.unit
    lines: list[str] = []

    lines.append("CLAIM CLASSIFICATION")
    lines.append(f"  Claim: {result.claim_id}")
    if result.branch:
        label = f"  Branch: {result.branch}"
        if result.variant:
            label += f" ({result.variant})"
        lines.append(label)
    if result.domain:
        lines.append(f"  Domain: {result.domain}")
    if result.route:
        lines.append(f"  Routed to: {result.route}")
    if result.formula_confidence is not None:
        lines.append(f"  Formula confidence: {result.formula_confidence:.2f}")
    if result.fields.get("classification"):
        basis = result.fields["classification"].get("basis") or []
        for item in basis:
            lines.append(f"    - {item}")
    lines.append("")

    lines.append("APPLICABLE RULES")
    if result.provenance:
        for entry in result.provenance:
            citation = _cite(entry)
            lines.append(f"  - {citation}")
    else:
        lines.append("  (no rule reached execution)")
    lines.append("")

    lines.append("CALCULATION")
    shown = 0
    for key, label in CALCULATION_ORDER:
        if key not in result.fields:
            continue
        value = result.fields[key]
        lines.append(f"  {label + ':':<48}{_fmt_value(key, value, unit)}")
        shown += 1
    if result.payable is not None:
        lines.append(f"  {'PAYABLE:':<48}{money.fmt(result.payable, unit)}")
    if result.payable_scenarios:
        lines.append(f"  {'SCENARIOS:':<48}{len(result.payable_scenarios)} outcomes")
        for index, scenario in enumerate(result.payable_scenarios):
            lines.append(f"    scenario {chr(ord('A') + index)}: {money.fmt(scenario, unit)}")
    if shown == 0 and result.payable is None and not result.payable_scenarios:
        lines.append("  (the claim was settled before valuation)")
    lines.append("")

    if result.status or result.reason:
        lines.append("STATUS")
        if result.status:
            lines.append(f"  {result.status}")
        if result.reason:
            lines.append(f"  {result.reason}")
        if result.labels:
            lines.append(f"  Labels: {', '.join(sorted(result.labels))}")
        lines.append("")

    escalation = render_escalation(result, kb)
    if escalation:
        lines.append("ESCALATION")
        for item in escalation:
            lines.append(f"  {item}")
        lines.append("")

    lines.append("SOURCES")
    seen: set[str] = set()
    for entry in result.provenance:
        for source_id in entry.get("sources") or []:
            if source_id in seen:
                continue
            seen.add(source_id)
            source = kb.source(source_id)
            if source is None:
                lines.append(f"  - {source_id} (not in the register)")
                continue
            lines.append(
                f"  - [{source.get('title')}] ({source_id}, tier={source.get('source_tier')})"
            )
            lines.append(f"    {source.get('url')}")
    if not seen:
        lines.append("  (no source cited)")

    return "\n".join(lines)


def render_escalation(result: CalcResult, kb: Knowledge) -> list[str]:
    items: list[str] = []
    for uncertainty_id in result.blocking_uncertainties:
        node = kb.uncertainty(uncertainty_id)
        if node is None:
            items.append(f"Unresolved variable {uncertainty_id} (node missing from the graph).")
            continue
        items.append(f"Blocking uncertainty {uncertainty_id}: {node.get('question')}")
        for scenario in node.get("scenarios") or []:
            items.append(f"    candidate outcome: {scenario}")
        artefact = node.get("resolution_artefact")
        if artefact:
            items.append(f"    resolves with: {artefact}")
    if result.blocking_uncertainties:
        items.append(
            "This claim requires insurer-specific validation before a single amount is payable."
        )
        items.append("Which insurer issued the policy? [insurer adapter unpopulated]")
    guard_violation = result.fields.get("guard_violation")
    if guard_violation:
        guard = kb.guards.get(guard_violation)
        if guard:
            items.append(f"Guardrail {guard_violation} refused the calculation: {guard.get('prevents')}")
    if result.status == "INPUT_ERROR":
        items.append("The case input is incomplete or contradictory; no calculation was attempted.")
    return items


def _cite(entry: dict[str, Any]) -> str:
    parts = [entry.get("node_id") or "?"]
    instrument = entry.get("instrument")
    article = entry.get("article")
    if instrument and article and article != "n/a":
        parts.append(f"{instrument} Art. {article}")
    elif instrument:
        parts.append(str(instrument))
    authority = entry.get("authority")
    if authority:
        parts.append(str(authority))
    confidence = entry.get("confidence")
    text = " - ".join(parts)
    if confidence is not None:
        text += f" [confidence {float(confidence):.2f}"
        if entry.get("derivation") and entry["derivation"] != "PRIMARY_TEXT":
            text += f", {entry['derivation']}"
        text += "]"
    return text


def _fmt_value(key: str, value: Any, unit: str) -> str:
    if isinstance(value, Decimal) and key not in NON_MONEY_INLINE:
        return money.fmt(value, unit)
    if isinstance(value, bool):
        return str(value)
    return str(value)
