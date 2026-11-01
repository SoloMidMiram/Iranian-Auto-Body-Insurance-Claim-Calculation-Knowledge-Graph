"""Shared evidence controls; identifying a source does not authenticate it."""
from typing import Any


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
