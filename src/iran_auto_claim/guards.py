"""Executable guardrails.

Each guard here is referenced by knowledge/guards.json (`enforced_in`), and the
loader verifies that the dotted path resolves, so a guardrail cannot be declared
without an implementation. A breach raises GuardViolation, which the engine turns
into a refusal rather than a number.
"""

from __future__ import annotations

from typing import Any

WHOLE_CAR_RATIO_KEYS = (
    "whole_car_ratio",
    "article8_whole_car_ratio",
    "proportional_ratio",
    "article8_proportional_ratio",
)

UNIVERSAL_GLASS_FRANCHISE_KEYS = (
    "glass_franchise_rate",
    "glass_only_franchise_rate",
    "universal_glass_franchise",
)

SOURCED_FRANCHISE_SOURCES = ("POLICY", "ENDORSEMENT", "INSURER_MANUAL")


class GuardViolation(Exception):
    def __init__(self, guard_id: str, message: str, violation_status: str) -> None:
        super().__init__(message)
        self.guard_id = guard_id
        self.violation_status = violation_status


def check_article8_method(case: Any) -> None:
    """Reject the whole-vehicle value ratio as the Article 8 method.

    The 1398/06/13 amendment requires component-wise corresponding damage. A case
    that hands the engine a luxury/conventional value ratio is asking it to apply
    the rejected method, so the engine refuses instead of computing.
    """
    for key in WHOLE_CAR_RATIO_KEYS:
        if case.field_value(key) is not None:
            raise GuardViolation(
                "G_ARTICLE8_NO_WHOLE_CAR_RATIO",
                (
                    f"case supplies {key!r}; the whole-car proportional method was replaced by "
                    "component-wise corresponding damage in the 1398/06/13 amendment"
                ),
                "GUARD_VIOLATION_ARTICLE8_METHOD",
            )
    method = str(case.config.get("article8_method", "")).upper()
    if method == "WHOLE_CAR_RATIO":
        raise GuardViolation(
            "G_ARTICLE8_NO_WHOLE_CAR_RATIO",
            "calculation_config.article8_method requests the rejected whole-car ratio method",
            "GUARD_VIOLATION_ARTICLE8_METHOD",
        )


def check_universal_glass_franchise(case: Any) -> None:
    """Reject an attempt to apply a universal glass franchise rate."""
    for key in UNIVERSAL_GLASS_FRANCHISE_KEYS:
        if case.field_value(key) is not None:
            raise GuardViolation(
                "G_NO_UNIVERSAL_GLASS_FRANCHISE",
                (
                    f"case requests {key!r}; Regulation 53 states no universal glass franchise "
                    "rate, so the rate must come from the policy or endorsement"
                ),
                "GUARD_VIOLATION_UNIVERSAL_GLASS_FRANCHISE",
            )


def check_franchise_source(case: Any, mode: str, source: str | None) -> None:
    """A percent-mode franchise must be traceable to a policy instrument."""
    if str(mode).upper() not in ("PERCENT", "PERCENT_WITH_MINIMUM"):
        return
    if (source or "UNKNOWN").upper() not in SOURCED_FRANCHISE_SOURCES:
        raise GuardViolation(
            "G_NO_HARDCODED_FRANCHISE_RATE",
            (
                f"percent franchise supplied with source {source or 'UNKNOWN'!r}; a rate must come "
                "from the policy, an endorsement or an insurer manual"
            ),
            "GUARD_VIOLATION_UNSOURCED_FRANCHISE_RATE",
        )


def check_covered_peril_causation(case: Any) -> None:
    """Require the positive covered-peril causal link before body arithmetic.

    This is deliberately separate from ``G_NO_ASSUMED_CAUSATION``, which guards
    whether an exclusion's own causal predicate has been established.
    """
    if case.covered_peril_causation_established is not True:
        raise GuardViolation(
            "G_COVERED_PERIL_CAUSATION_ESTABLISHED",
            "the covered peril's causal relationship to this damage is not established",
            "COVERED_PERIL_CAUSATION_REQUIRED",
        )


def check_recovery_allocation(case: Any) -> None:
    """Contain unimplemented prior-recovery and multiple-policy settlement paths."""
    facts = case.multiple_insurance
    state = case.multiple_insurance_state
    prior = case.prior_compensation
    if facts is None or state in (None, "UNKNOWN") or prior is None:
        raise GuardViolation(
            "G_RECOVERY_ALLOCATION_CONTAINED",
            "other-policy state and prior compensation from any source must both be recorded",
            "RECOVERY_FACTS_REQUIRED",
        )
    if prior > 0:
        raise GuardViolation(
            "G_RECOVERY_ALLOCATION_CONTAINED",
            (
                "positive prior compensation is recorded, but no approved remainder or "
                "coordination operator is implemented"
            ),
            "PRIOR_COMPENSATION_SETTLEMENT_UNSUPPORTED",
        )
    if state in ("YES_OTHER_POLICIES", "YES_SAME_INSURER"):
        raise GuardViolation(
            "G_RECOVERY_ALLOCATION_CONTAINED",
            (
                "another policy is recorded; settlement followed by contribution may be "
                "legally available, but that implementation is not present"
            ),
            "MULTIPLE_INSURANCE_CONTRIBUTION_NOT_IMPLEMENTED",
        )
    if state != "NO":
        raise GuardViolation(
            "G_RECOVERY_ALLOCATION_CONTAINED",
            f"unsupported multiple-insurance state {state!r}",
            "RECOVERY_FACTS_REQUIRED",
        )


def check_uncertainty_propagation(result: Any) -> None:
    """A live blocking uncertainty must never coexist with a single payable.

    This is the safety net behind the "no false precision" rule: if a blocking
    uncertainty surfaced, the result must be a scenario set or a refusal.
    """
    if result.blocking_uncertainties and result.payable is not None:
        raise GuardViolation(
            "G_UNCERTAINTY_MUST_SURFACE",
            (
                "blocking uncertainties "
                + ", ".join(result.blocking_uncertainties)
                + " are live but a single payable was produced"
            ),
            "GUARD_VIOLATION_HIDDEN_UNCERTAINTY",
        )


GUARD_CHECKS = {
    "G_ARTICLE8_NO_WHOLE_CAR_RATIO": check_article8_method,
    "G_NO_UNIVERSAL_GLASS_FRANCHISE": check_universal_glass_franchise,
    "G_NO_HARDCODED_FRANCHISE_RATE": check_franchise_source,
    "G_COVERED_PERIL_CAUSATION_ESTABLISHED": check_covered_peril_causation,
    "G_RECOVERY_ALLOCATION_CONTAINED": check_recovery_allocation,
    "G_UNCERTAINTY_MUST_SURFACE": check_uncertainty_propagation,
}
