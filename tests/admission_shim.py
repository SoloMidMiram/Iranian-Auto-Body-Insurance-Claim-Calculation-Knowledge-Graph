"""Shared admission shim for engine-level tests.

These tests exercise arithmetic, guards, plans and provenance - not the review
questionnaire. They still must not bypass the authorization boundary, so every
call goes through ``engine_direct_authorize``, the same narrow direct channel
``fixtures.py`` and ``claim.py calc`` use. The authorization is real and
hash-verified; only its issuer differs from ``REVIEW_GATE``.

Keeping the local name ``compute`` means a test that asserts an amount reads the
same as before the boundary existed, while the boundary is still enforced.
"""

from __future__ import annotations

from typing import Any

from iran_auto_claim.admission import engine_direct_authorize
from iran_auto_claim.case import Case
from iran_auto_claim.engine import CalcResult
from iran_auto_claim.engine import compute as compute_authorized
from iran_auto_claim.knowledge import Knowledge


def compute(case: Case | dict[str, Any], kb: Knowledge | None = None) -> CalcResult:
    """Authorize through the direct channel, then run the engine."""
    return compute_authorized(engine_direct_authorize(case, kb), kb)


__all__ = ["compute", "compute_authorized", "engine_direct_authorize"]
