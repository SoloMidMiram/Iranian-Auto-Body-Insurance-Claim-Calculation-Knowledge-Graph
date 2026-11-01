"""Shared evidence controls; identifying a source does not authenticate it."""
from typing import Any
import re

from .dates import CalendarDateError, parse_claim_date


def franchise_identity_gap(spec: Any) -> str | None:
    """Require reproducible instrument identity for every monetary term, even zero.

    This is one necessary condition, not a statement that reference/version alone
    prove insurer, product, date or contractual applicability.
    """
    if not isinstance(spec, dict):
        return "a structured policy or endorsement franchise term is required"
    if spec.get("source") not in ("POLICY", "ENDORSEMENT", "INSURER_MANUAL"):
        return "the franchise source is not an identified contractual instrument"
    for field in ("source_reference", "source_version"):
        value = spec.get(field)
        if not isinstance(value, str) or not value.strip():
            return f"franchise authority requires a nonblank {field} for the invoked instrument"
    return None


def applicability_gap(record: Any, context: dict, event_date: Any, branch: str,
                      terms: dict) -> str | None:
    """Validate a recorded source review, never infer authentication from a label.

    VERIFIED is a recorded reviewer attestation, not authentication performed by
    this function. Synthetic records must remain explicitly synthetic in context.
    """
    if not isinstance(record, dict):
        return "an applicable reviewed contractual authority record is required"
    for field in ("source_reference", "source_version", "insurer", "product",
                  "clause_locator", "reviewer"):
        if not isinstance(record.get(field), str) or not record[field].strip():
            return f"authority record requires {field}"
    if not re.fullmatch(r"[0-9a-f]{64}", str(record.get("document_sha256", ""))):
        return "authority record requires a preserved document SHA-256"
    if record.get("source_status") == "SYNTHETIC_TEST":
        if context.get("contract_kind") != "SYNTHETIC_TEST":
            return "synthetic authority cannot govern an unmarked insurance contract"
    elif record.get("source_status") != "VERIFIED":
        return "source authentication/applicability review remains unresolved"
    if record.get("governs_contract") is not True:
        return "the instrument has not been established as governing this contract"
    for field in ("insurer", "product", "policy_reference"):
        if not context.get(field) or context[field] != record.get(field):
            return f"authority {field} does not match the claim contract"
    if branch not in (record.get("coverage") or []):
        return "authority coverage/claim type does not include the selected branch"
    if record.get("terms") != terms:
        return "authority terms conflict with the selected monetary term or order"
    try:
        start = parse_claim_date(record.get("effective_from")).chronology_key
        end = parse_claim_date(record.get("effective_until")).chronology_key
        occurred = parse_claim_date(event_date).chronology_key
        policy_date = parse_claim_date(context.get("policy_date")).chronology_key
    except (CalendarDateError, TypeError, ValueError):
        return "authority effective interval, policy date and event date must be established"
    if start > end or not (start <= occurred <= end and start <= policy_date <= end):
        return "authority effective interval does not cover the policy and event dates"
    return None


FRANCHISE_TERM_FIELDS = (
    "mode", "absolute_irr", "absolute", "rate", "minimum_irr", "minimum",
    "calculation_base", "claim_sequence_rule", "coverage_specific_rule",
)


def franchise_terms(spec: dict) -> dict:
    return {key: spec[key] for key in FRANCHISE_TERM_FIELDS if key in spec}


def franchise_applicability_gap(spec: Any, context: dict, event_date: Any,
                                branch: str) -> str | None:
    if gap := franchise_identity_gap(spec):
        return gap
    record = spec.get("authority")
    if isinstance(record, dict):
        for field in ("source_reference", "source_version"):
            if record.get(field) != spec.get(field):
                return f"franchise {field} conflicts with the reviewed authority record"
    return applicability_gap(record, context, event_date, branch, franchise_terms(spec))
