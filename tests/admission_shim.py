"""Shared admission shim for engine-level tests.

These tests exercise arithmetic, guards, plans and provenance rather than the
questionnaire. Every call receives a schema-validated authorization from the
private ``INTERNAL_TEST_DIRECT`` path used by the fixture corpus. It is visibly
different from a review-issued authorization and unavailable from the package API.

Keeping the local name ``compute`` means a test that asserts an amount reads the
same as before the boundary existed, while the boundary is still enforced.
"""

from __future__ import annotations

from typing import Any

from iran_auto_claim.case import Case
from iran_auto_claim.engine import CalcResult
from iran_auto_claim.engine import compute as compute_authorized
from iran_auto_claim.fixtures import _authorize_fixture_case
from iran_auto_claim.knowledge import Knowledge


def compute(case: Case | dict[str, Any], kb: Knowledge | None = None) -> CalcResult:
    """Authorize through the internal test-only path, then run the engine."""
    knowledge = kb or Knowledge.load()
    raw = case.raw if isinstance(case, Case) else case
    return compute_authorized(_authorize_fixture_case(raw, knowledge), knowledge)


__all__ = ["compute", "compute_authorized", "_authorize_fixture_case"]
