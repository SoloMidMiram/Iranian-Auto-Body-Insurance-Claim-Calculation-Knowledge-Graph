"""Branch engines.

The top-level shape is the one the report specifies:

    EVENT -> LEGAL/POLICY SNAPSHOT -> COVERAGE + CAUSATION + EXCLUSION GATE
         -> CLAIM BRANCH CLASSIFICATION -> BRANCH-SPECIFIC VALUATION
         -> COMPONENT CLASSIFICATION -> APPLICABLE OPERATORS
         -> CONFIGURABLE OPERATOR ORDER -> STATUTORY/CONTRACTUAL CAPS
         -> DUAL-COVERAGE ALLOCATION -> SUBROGATION
         -> PAYABLE + RULE TRACE + PROVENANCE + CONFIDENCE + UNRESOLVED VARIABLES

Design commitments enforced here:

* A branch may only return one number when its operator order is resolved, or
  when the unresolved operator provably does not change the outcome (the
  underinsurance ratio equal to 1).
* A blocking uncertainty always surfaces as payable=None with either scenarios or
  a refusal status. It is never averaged away.
* Confidence is computed from the trace, not asserted: the minimum of the
  cited rules' confidences and the live blocking uncertainties' single-
  interpretation confidences.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from . import guards, money, operators
from .admission import (
    AuthorizationError,
    CalculationAuthorization,
)
from .case import DOMAIN_BY_BRANCH, Case, CaseInputError
from .authority import applicability_gap, franchise_applicability_gap, franchise_identity_gap
from .classify import ClassificationEvidenceRequired, classify
from .dates import CalendarDateError, is_shamsi_leap_year, parse_claim_date
from .knowledge import Knowledge
from .plans import (
    FRANCHISE,
    RATIO,
    PlanError,
    graph_partial_payable,
    graph_total_loss_payable,
    named_sequence,
    plan_identity,
    sequences_with_ratio,
    validate_body_sequence,
)
from .schema_input import validated_case

UNRESOLVED_ORDER = "UNRESOLVED"
RESOLVED_PARTIAL_ORDERS = frozenset(
    {"AFTER_DEPRECIATION_BEFORE_FRANCHISE", "AFTER_DEPRECIATION_AND_FRANCHISE"}
)


@dataclass
class CalcResult:
    branch: str | None = None
    variant: str | None = None
    domain: str | None = None
    claim_id: str | None = None
    unit: str = "IRR"
    payable: Decimal | None = None
    payable_scenarios: list[Decimal] = field(default_factory=list)
    status: str | None = None
    reason: str | None = None
    route: str | None = None
    labels: set[str] = field(default_factory=set)
    fields: dict[str, Any] = field(default_factory=dict)
    rule_trace: list[str] = field(default_factory=list)
    blocking_uncertainties: list[str] = field(default_factory=list)
    formula_confidence: float | None = None
    evidence_confidence: float | None = None
    provenance: list[dict[str, Any]] = field(default_factory=list)
    required_guards: list[str] = field(default_factory=list)
    guards_executed: list[str] = field(default_factory=list)
    authorization: dict[str, Any] = field(default_factory=dict)

    def label(self, *names: str) -> None:
        for name in names:
            if name:
                self.labels.add(name)

    def note_guard(self, guard_id: str) -> None:
        if guard_id and guard_id not in self.guards_executed:
            self.guards_executed.append(guard_id)

    def require_guard(self, *guard_ids: str) -> None:
        for guard_id in guard_ids:
            if guard_id and guard_id not in self.required_guards:
                self.required_guards.append(guard_id)

    def note_rule(self, *rule_ids: str) -> None:
        for rule_id in rule_ids:
            if rule_id and rule_id not in self.rule_trace:
                self.rule_trace.append(rule_id)

    def block(self, *uncertainty_ids: str) -> None:
        for uncertainty_id in uncertainty_ids:
            if uncertainty_id and uncertainty_id not in self.blocking_uncertainties:
                self.blocking_uncertainties.append(uncertainty_id)

    @property
    def payable_is_single(self) -> bool:
        return self.payable is not None

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "branch": self.branch,
            "variant": self.variant,
            "domain": self.domain,
            "unit": "IRR",
            "payable_irr": _out(self.payable),
            "payable_scenarios_irr": [_out(value) for value in self.payable_scenarios],
            "status": self.status,
            "reason": self.reason,
            "route": self.route,
            "labels": sorted(self.labels),
            "fields": {key: _out(value) for key, value in sorted(self.fields.items())},
            "rule_trace": list(self.rule_trace),
            "blocking_uncertainties": list(self.blocking_uncertainties),
            "formula_confidence": self.formula_confidence,
            "evidence_confidence": self.evidence_confidence,
            "provenance": _out(self.provenance),
            "required_guards": list(self.required_guards),
            "guards_executed": list(self.guards_executed),
            "authorization": dict(self.authorization),
        }


def _out(value: Any) -> Any:
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else format(value, "f")
    if isinstance(value, dict):
        return {key: _out(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_out(item) for item in value]
    return value


def _activate_body_plan(
    res: CalcResult,
    branch_name: str,
    branch_plan: dict[str, Any],
    sequences: list[str] | list[list[str]],
) -> list[str] | list[list[str]]:
    """Validate, identify, and bind the guards for an active body plan."""
    expected = [str(item) for item in branch_plan.get("operators") or []]
    guards_required = [str(item) for item in branch_plan.get("guardrails") or []]
    if not expected:
        raise PlanError(f"body branch {branch_name} has no operator sequence")
    if sequences and isinstance(sequences[0], list):
        validated = [
            validate_body_sequence(branch_name, list(sequence), expected)
            for sequence in sequences
        ]
        res.fields["execution_plan"] = validated
        res.fields["execution_plan_ids"] = [
            plan_identity(branch_name, sequence, guards_required) for sequence in validated
        ]
    else:
        validated = validate_body_sequence(branch_name, list(sequences), expected)
        res.fields["execution_plan"] = validated
        res.fields["execution_plan_id"] = plan_identity(
            branch_name, validated, guards_required
        )
    res.fields["execution_plan_branch"] = branch_name
    res.fields["execution_plan_guards"] = guards_required
    res.require_guard(*guards_required)
    return validated


def _enforce_guard_plan(res: CalcResult) -> None:
    missing = [
        guard_id for guard_id in res.required_guards if guard_id not in res.guards_executed
    ]
    if not missing:
        return
    res.payable = None
    res.payable_scenarios = []
    res.status = "GUARD_PLAN_INCOMPLETE"
    res.reason = "required guard did not run: " + ", ".join(missing)
    res.fields["missing_required_guards"] = missing
    res.label("GUARD_PLAN_INCOMPLETE")


# --------------------------------------------------------------------- helpers


def _rescue(
    case: Case,
    res: CalcResult,
    candidate_bases: dict[str, Decimal],
) -> Decimal:
    actual = case.rescue_actual
    supplied_payable = case.rescue_payable
    if actual is not None and supplied_payable is not None and supplied_payable > actual:
        raise operators.OperatorError(
            "supplied rescue payable exceeds the separately supplied actual expense"
        )
    configured = case.config.get("rescue_cap_base")
    if configured is None:
        if supplied_payable is not None:
            candidate_amounts = {
                name: (
                    min(supplied_payable, operators.RESCUE_CAP_RATIO * base)
                    if base > 0
                    else Decimal(0)
                )
                for name, base in candidate_bases.items()
            }
        else:
            candidate_amounts = {
                name: operators.allowable_rescue_transport(actual, base)
                for name, base in candidate_bases.items()
            }
        if len(set(candidate_amounts.values())) > 1:
            res.fields["rescue_candidate_amounts"] = candidate_amounts
            raise operators.UncertaintyRequired(
                "U05_RESCUE_DENOMINATOR",
                (
                    "the rescue ceiling denominator is missing and the candidate "
                    "bases change the payable amount"
                ),
                status="RESCUE_DENOMINATOR_UNRESOLVED",
                scenarios=list(candidate_bases),
            )
        cap_kind = "CANDIDATES_EQUIVALENT"
        cap_base = min(candidate_bases.values()) if candidate_bases else Decimal(0)
    else:
        cap_kind = str(configured).upper()
        if cap_kind not in candidate_bases:
            raise operators.OperatorError(
                f"rescue cap base {cap_kind!r} is not available for this calculation branch"
            )
        cap_base = candidate_bases[cap_kind]

    cap_limit = operators.RESCUE_CAP_RATIO * cap_base if cap_base > 0 else Decimal(0)
    if supplied_payable is not None:
        if supplied_payable > cap_limit:
            raise operators.OperatorError(
                "supplied rescue payable exceeds the applicable rescue ceiling"
            )
        rescue = supplied_payable
    else:
        rescue = operators.allowable_rescue_transport(actual, cap_base)
    res.fields["rescue_cap_base_kind"] = cap_kind
    res.fields["rescue_cap_base"] = cap_base
    res.fields["rescue_cap"] = cap_limit
    res.fields["allowable_rescue_transport"] = rescue
    res.fields["rescue_claimed"] = actual
    res.fields["rescue_payable_supplied"] = supplied_payable
    res.fields["rescue_input_kind"] = (
        "ACTUAL_AND_PAYABLE"
        if actual is not None and supplied_payable is not None
        else "ACTUAL"
        if actual is not None
        else "PAYABLE"
        if supplied_payable is not None
        else "NONE"
    )
    res.note_guard("G_RESCUE_CAP_CEILING")
    if (actual or Decimal(0)) > 0 or (supplied_payable or Decimal(0)) > 0:
        res.note_rule("REG53_RESCUE_TRANSPORT_CAP")
        if supplied_payable is None and actual is not None and rescue < actual:
            res.label("RESCUE_CAPPED")
    return rescue


def _ratio(case: Case, res: CalcResult) -> Decimal:
    """Apply the underinsurance ratio only from both required value anchors."""
    market = case.market_value
    insured = case.insured_sum
    if market is None and insured is None:
        raise operators.OperatorError(
            "market value and insured sum are required to assess the Article 10 underinsurance ratio"
        )
    ratio = operators.underinsurance_ratio(insured, market)
    res.fields["article10_ratio"] = ratio
    res.note_rule("REG53_ART20_NOTE2_UNDERINSURANCE_RATIO")
    if ratio < 1:
        res.label("UNDERINSURANCE_APPLIED")
    return ratio


def _resolve_franchise(
    case: Case,
    res: CalcResult,
    bases: dict[str, Decimal],
) -> Decimal:
    raw = case.franchise_raw
    spec: dict[str, Any] | None = None
    source: str | None = None

    if isinstance(raw, dict):
        spec = dict(raw)
        source = spec.get("source")
    elif raw is not None:
        spec = {"mode": "ABSOLUTE", "absolute_irr": raw}
        source = "CASE_INPUT"
    elif case.policy_franchise is not None:
        spec = dict(case.policy_franchise)
        source = spec.get("source")
    elif case.config.get("franchise_rate") is not None:
        spec = {"mode": "PERCENT", "rate": case.config["franchise_rate"]}
        source = None

    if spec is None:
        res.fields["franchise_source"] = "NOT_SPECIFIED"
        res.fields["franchise_evidence_needed"] = (
            "policy/product/version franchise schedule or endorsement"
        )
        raise operators.UncertaintyRequired(
            "U02_FRANCHISE_BASE_SCHEDULES",
            (
                "franchise terms are missing; supply the applicable policy or endorsement "
                "schedule for the insurer, product and version"
            ),
            status="FRANCHISE_TERMS_REQUIRED",
        )

    mode = str(spec.get("mode", "ABSOLUTE")).upper()
    res.fields["franchise_evidence_needed"] = (
        "policy/product/version franchise schedule or endorsement"
    )
    if mode in ("PERCENT", "PERCENT_WITH_MINIMUM") and spec.get("rate") is None:
        raise operators.UncertaintyRequired(
            "U02_FRANCHISE_BASE_SCHEDULES",
            "the percentage franchise rate is missing from the applicable policy schedule",
            status="FRANCHISE_TERMS_REQUIRED",
        )
    calculation_base = spec.get("calculation_base")
    if mode in ("PERCENT", "PERCENT_WITH_MINIMUM"):
        if calculation_base is None:
            raise operators.UncertaintyRequired(
                "U02_FRANCHISE_BASE_SCHEDULES",
                "the percentage franchise calculation base is missing from the policy schedule",
                status="FRANCHISE_BASE_REQUIRED",
            )
        calculation_base = str(calculation_base).upper()
        if calculation_base not in bases:
            raise operators.UncertaintyRequired(
                "U02_FRANCHISE_BASE_SCHEDULES",
                f"franchise calculation base {calculation_base!r} is not available for this branch",
                status="FRANCHISE_BASE_UNSUPPORTED",
            )
    if mode == "PERCENT_WITH_MINIMUM" and spec.get("minimum_irr", spec.get("minimum")) is None:
        raise operators.UncertaintyRequired(
            "U02_FRANCHISE_BASE_SCHEDULES",
            "the minimum amount for the percentage-with-minimum franchise is missing",
            status="FRANCHISE_TERMS_REQUIRED",
        )
    if mode == "ABSOLUTE" and spec.get("absolute_irr", spec.get("absolute")) is None:
        raise operators.UncertaintyRequired(
            "U02_FRANCHISE_BASE_SCHEDULES",
            "the absolute franchise amount is missing from the applicable policy schedule",
            status="FRANCHISE_TERMS_REQUIRED",
        )
    res.require_guard("G_NO_HARDCODED_FRANCHISE_RATE")
    guards.check_franchise_source(case, mode, source)
    res.note_guard("G_NO_HARDCODED_FRANCHISE_RATE")
    if source not in guards.SOURCED_FRANCHISE_SOURCES:
        res.fields["franchise_source"] = source or "UNKNOWN"
        res.fields["franchise_evidence_needed"] = (
            "policy/product/version franchise schedule or endorsement"
        )
        raise operators.UncertaintyRequired(
            "U02_FRANCHISE_BASE_SCHEDULES",
            "the franchise has no authorised policy, endorsement or insurer-manual source",
            status="FRANCHISE_AUTHORITY_REQUIRED",
        )

    if gap := franchise_identity_gap(spec):
        res.fields["franchise_source"] = source or "UNKNOWN"
        raise operators.UncertaintyRequired(
            "U02_FRANCHISE_BASE_SCHEDULES", gap,
            status="FRANCHISE_AUTHORITY_REQUIRED",
        )

    if gap := franchise_applicability_gap(spec, case.policy, case.event.get("event_date"), res.branch):
        res.fields["franchise_authority_gap"] = gap
        raise operators.UncertaintyRequired(
            "U02_FRANCHISE_BASE_SCHEDULES", gap,
            status="FRANCHISE_AUTHORITY_REQUIRED",
        )
    res.fields["franchise_authority_source_status"] = spec["authority"]["source_status"]
    res.fields["franchise_authority"] = dict(spec["authority"])

    def _dec(value: Any) -> Decimal | None:
        return None if value is None else money.D(value)

    selected_base = bases.get(str(calculation_base).upper()) if calculation_base else None
    amount = operators.franchise_amount(
        mode,
        base=selected_base,
        rate=_dec(spec.get("rate")),
        absolute=_dec(spec.get("absolute_irr", spec.get("absolute"))),
        minimum=_dec(spec.get("minimum_irr", spec.get("minimum"))),
    )
    if amount == 0:
        version = spec.get("source_version") or case.policy.get("policy_version")
        reference = spec.get("source_reference")
        if source not in guards.SOURCED_FRANCHISE_SOURCES or not version or not reference:
            res.fields["franchise_source"] = source or "UNKNOWN"
            res.fields["franchise_evidence_needed"] = (
                "versioned policy or endorsement reference explicitly stating zero franchise"
            )
            raise operators.UncertaintyRequired(
                "U02_FRANCHISE_BASE_SCHEDULES",
                (
                    "zero franchise must be explicit in a referenced policy or endorsement "
                    "for the applicable product version"
                ),
                status="FRANCHISE_AUTHORITY_REQUIRED",
            )
    res.fields["franchise"] = amount
    res.fields["franchise_mode"] = mode
    res.fields["franchise_source"] = source or "UNKNOWN"
    res.fields["franchise_calculation_base_kind"] = (
        str(calculation_base).upper() if calculation_base else "NOT_APPLICABLE"
    )
    if selected_base is not None:
        res.fields["franchise_calculation_base"] = selected_base
    if spec.get("source_version"):
        res.fields["franchise_source_version"] = spec["source_version"]
    res.note_rule("REG53_POLICY_DEFINED_FRANCHISE")
    return amount


def _threshold(case: Case, kb: Knowledge) -> Decimal | None:
    given = case.threshold
    if given is not None:
        return given
    irr = kb.annual_value(case.claim_year, "CONVENTIONAL_THRESHOLD")
    if irr is None:
        return None
    return money.D(irr)


# ---------------------------------------------------------------- coverage gate


def _exclusion_matches(case: Case, exclusion: dict[str, Any]) -> bool:
    predicate = exclusion.get("cause_predicate") or {}
    checks: list[bool] = []

    theft_types = predicate.get("theft_type_in")
    if theft_types:
        checks.append(case.theft_type in theft_types)

    field = predicate.get("field")
    if field:
        value = case.field_value(field)
        checks.append(value is not None and value == predicate.get("equals"))

    tokens = predicate.get("cause_in") or []
    if tokens:
        observed = {
            str(value).casefold()
            for value in (case.cause, case.peril)
            if value not in (None, "")
        }
        checks.append(any(str(token).casefold() in observed for token in tokens))

    # Clauses in one predicate describe one factual condition. Intoxication,
    # for example, needs both the coded cause and the causal authority finding.
    return bool(checks) and all(checks)


def enforce_body_eligibility_admission(case: Case, res: CalcResult) -> None:
    """Run body admission predicates that must hold before any exclusion or amount.

    Positive covered-peril causation and exclusion causation are different facts.
    The former is checked here; ``evaluate_coverage_gate`` retains the latter.
    Recovery containment likewise chooses no allocation formula: it only prevents
    an unsupported recovery or contribution state from reaching settlement.
    """
    # Register each guard immediately before its check. If the first predicate
    # fails, the second predicate has not run and must not replace the
    # defect-specific status with GUARD_PLAN_INCOMPLETE during finalization.
    res.require_guard("G_COVERED_PERIL_CAUSATION_ESTABLISHED")
    res.fields["covered_peril_causation_established"] = (
        case.covered_peril_causation_established
    )
    guards.check_covered_peril_causation(case)
    res.note_guard("G_COVERED_PERIL_CAUSATION_ESTABLISHED")

    res.require_guard("G_RECOVERY_ALLOCATION_CONTAINED")
    res.fields["multiple_insurance_state"] = case.multiple_insurance_state
    res.fields["prior_compensation"] = case.prior_compensation
    res.note_rule("REG53_ART21_MULTIPLE_INSURANCE_CONTRIBUTION")
    guards.check_recovery_allocation(case)
    res.note_guard("G_RECOVERY_ALLOCATION_CONTAINED")


def evaluate_coverage_gate(case: Case, kb: Knowledge, res: CalcResult) -> bool:
    """Coverage, causation and exclusion gate. Returns True when it settles the claim."""
    # Article 6 non-compensable circumstances defeat cover outright.
    for exclusion in kb.exclusions.values():
        if exclusion.get("type") != "NON_COMPENSABLE":
            continue
        if _exclusion_matches(case, exclusion):
            res.require_guard("G_NO_ASSUMED_CAUSATION")
            outcome = exclusion["uninsured_outcome"]
            res.payable = money.D(outcome.get("payable", 0))
            res.reason = outcome.get("reason", "NON_COMPENSABLE")
            res.fields["exclusion_applied"] = exclusion["node_id"]
            res.fields["exclusion_state"] = "NON_COMPENSABLE"
            res.note_rule("REG53_ART6_NON_COMPENSABLE")
            res.note_guard("G_NO_ASSUMED_CAUSATION")
            res.label("NON_COMPENSABLE")
            return True

    # Article 5 risks are excluded from the base cover but restorable by endorsement.
    for exclusion in kb.exclusions.values():
        if exclusion.get("type") != "EXCLUDED_BUT_ENDORSABLE":
            continue
        if not _exclusion_matches(case, exclusion):
            continue
        res.fields["exclusion_applied"] = exclusion["node_id"]
        res.fields["exclusion_state"] = "EXCLUDED_BUT_ENDORSABLE"
        res.note_rule("REG53_ART5_ENDORSABLE_EXCLUSIONS")
        if case.has_endorsement(list(exclusion.get("restorable_by") or [])):
            res.require_guard("G_NO_GUESSED_ENDORSEMENT_TERMS")
            outcome = exclusion.get("insured_outcome") or {}
            res.payable = None
            res.status = outcome.get("status", "ENDORSEMENT_TERMS_REQUIRED")
            res.note_guard("G_NO_GUESSED_ENDORSEMENT_TERMS")
            res.label("ENDORSEMENT_TERMS_REQUIRED")
            res.fields["endorsement_terms_needed"] = exclusion.get("endorsement_terms_needed", [])
            res.block("U02_FRANCHISE_BASE_SCHEDULES")
            return True
        outcome = exclusion["uninsured_outcome"]
        res.payable = money.D(outcome.get("payable", 0))
        res.reason = outcome.get("reason", "EXCLUDED_WITHOUT_ENDORSEMENT")
        res.label("EXCLUDED_WITHOUT_ENDORSEMENT")
        return True

    adjudications: list[str] = []
    if case.late_notice_issue:
        res.label("LATE_NOTICE_REVIEW")
        res.note_rule("REG53_NOTICE_AND_DUTIES")
        adjudications.append("NOTICE_ADJUDICATION_REQUIRED")
    if case.subrogation_impaired:
        res.label("SUBROGATION_IMPAIRMENT_REVIEW")
        res.note_rule("REG53_ART14_SUBROGATION")
        adjudications.append("SUBROGATION_ADJUDICATION_REQUIRED")
    if res.domain == "BODY" and adjudications:
        res.payable = None
        res.status = adjudications[0]
        res.fields["eligibility_blocking_conditions"] = adjudications
        res.reason = "affected notice/recovery predicates require reviewed adjudication before calculation"
        return True
    return False


# ------------------------------------------------- risk intensification (U15)


def check_risk_intensification(case: Case, kb: Knowledge) -> None:
    """Fail closed when an unnotified risk intensification reaches the arithmetic.

    ``U15_RISK_INTENSIFICATION_PREMIUM_RATIO`` reduces payment by the ratio of
    the premium charged to the premium appropriate to the intensified risk. That
    is a premium-ratio operator, not underinsurance, and this engine does not
    implement it - the uncertainty node records ``NOT_IMPLEMENTED_DO_NOT_SUBSTITUTE``.
    No claim-case field carries the charged or tariff premium, so the condition
    can never be resolved at the calculation boundary today.

    Raising here means a file that records intensification cannot be settled at
    the full amount by an authorization that was issued through the direct
    channel. It surfaces as a blocked uncertainty with no single payable.

    The candidate scenarios are read from the graph node rather than restated in
    code: `validate()` already requires every blocking uncertainty to declare
    them, so duplicating the wording here would let the two drift apart.
    """
    if not case.risk_intensified:
        return
    node = kb.uncertainty("U15_RISK_INTENSIFICATION_PREMIUM_RATIO") or {}
    raise operators.UncertaintyRequired(
        "U15_RISK_INTENSIFICATION_PREMIUM_RATIO",
        (
            "the risk intensified without notification, and payment must be reduced by the "
            "ratio of the premium charged to the premium appropriate to that risk; this engine "
            "does not implement that premium-ratio operator and will not substitute the "
            "underinsurance ratio for it"
        ),
        status="RISK_INTENSIFICATION_PREMIUM_RATIO_UNRESOLVED",
        scenarios=[str(item) for item in node.get("scenarios") or []],
    )


# ------------------------------------------------------------- partial damage


def calculate_partial_damage(case: Case, kb: Knowledge, res: CalcResult) -> None:
    res.label("PARTIAL_DAMAGE")
    res.note_rule("REG53_ART19B_PARTIAL_LOSS_BASE")
    if case.damage.get("depreciation_method") == "ASSESSED_FIGURE":
        if case.assessed_depreciation is None or case.parts:
            res.payable = None
            res.status = ("ASSESSED_DEPRECIATION_AMOUNT_REQUIRED" if case.assessed_depreciation is None
                          else "ASSESSED_DEPRECIATION_METHOD_UNRESOLVED")
            res.reason = "the selected assessor route cannot silently become computed-per-part depreciation"
            return

    parts = case.parts
    labor = case.labor or Decimal(0)

    assessed = Decimal(0)
    eligible = Decimal(0)
    computed_depreciation = Decimal(0)
    glass_depreciation = Decimal(0)
    other_depreciation = Decimal(0)

    for part in parts:
        assessed += money.D(part["assessed_loss"])
        info = operators.eligible_part_loss(
            part, case.production_year, case.claim_year, case.config
        )
        eligible += info["capped_loss"]
        computed_depreciation += info["depreciation_amount"]
        if part["category"] in operators.DEPRECIATION_EXEMPT_CATEGORIES:
            glass_depreciation += info["depreciation_amount"]
        else:
            other_depreciation += info["depreciation_amount"]
        if part["category"] in operators.SPECIAL_CAP_CATEGORIES:
            res.note_rule("REG53_ART3_5_BATTERY_TIRE_SPECIAL_CAP")
            res.label(f"{part['category']}_50_PERCENT_CAP", "SPECIAL_PART_CAP_APPLIED")

    if parts:
        eligible += labor
        assessed += labor
        if case.gross_damage is not None:
            res.label("ITEMISED_PARTS_USED")
    else:
        aggregate = case.gross_damage if case.gross_damage is not None else case.labor
        if aggregate is None:
            raise operators.OperatorError(
                "partial damage needs itemised parts, a labour figure or an aggregate gross damage figure"
            )
        eligible = aggregate
        assessed = aggregate

    if parts:
        depreciation = computed_depreciation
        res.fields["depreciation_source"] = "COMPUTED_PER_PART"
        res.fields["glass_depreciation"] = glass_depreciation
        res.fields["other_depreciation"] = other_depreciation
        res.note_rule("REG53_ART19_REPLACEMENT_PART_DEPRECIATION")
    elif case.assessed_depreciation is not None:
        depreciation = case.assessed_depreciation
        res.fields["depreciation_source"] = "EXPLICIT"
    elif case.depreciable_parts is not None and case.depreciation_rate is not None:
        depreciation = operators.depreciation_amount(case.depreciable_parts, case.depreciation_rate)
        res.fields["depreciation_source"] = "BASE_TIMES_RATE"
        res.note_rule("REG53_ART19_REPLACEMENT_PART_DEPRECIATION")
    else:
        raise operators.OperatorError(
            "aggregate partial damage requires explicit assessed depreciation or a depreciation base and rate"
        )

    after_depreciation = eligible - depreciation
    res.fields["assessed_gross"] = assessed
    res.fields["gross_eligible"] = eligible
    res.fields["eligible_before_other_terms"] = eligible
    res.fields["depreciation"] = depreciation
    res.fields["after_depreciation"] = after_depreciation

    if assessed != eligible:
        res.label("RESCUE_DENOMINATOR_CONFIGURED")
    rescue = _rescue(
        case,
        res,
        {
            "ASSESSED_GROSS": assessed,
            "ELIGIBLE_GROSS": eligible,
            "SETTLEMENT_BASE": after_depreciation,
        },
    )

    franchise = _resolve_franchise(
        case,
        res,
        {
            "ASSESSED_GROSS": assessed,
            "GROSS_ELIGIBLE": eligible,
            "AFTER_DEPRECIATION": after_depreciation,
            "SETTLEMENT_BASE": after_depreciation,
        },
    )
    ratio = _ratio(case, res)
    order = str(case.config.get("article10_partial_order", UNRESOLVED_ORDER)).upper()

    branch_plan = kb.branch("PARTIAL_DAMAGE") or {}
    if ratio == 1:
        res.fields["order_used"] = "RATIO_NOT_APPLICABLE"
        sequence = _activate_body_plan(
            res,
            "PARTIAL_DAMAGE",
            branch_plan,
            list(branch_plan.get("operators") or []),
        )
        res.payable = graph_partial_payable(
            after_depreciation, franchise, ratio, rescue, sequence
        )
        return

    sequence = named_sequence(branch_plan, order)
    order_gap = applicability_gap(
        case.config.get("article10_order_authority"), case.policy,
        case.event.get("event_date"), "PARTIAL_DAMAGE",
        {"article10_partial_order": order},
    )
    res.fields["article10_order_authority_gap"] = order_gap
    if sequence and RATIO in sequence and FRANCHISE in sequence and order_gap is None:
        res.fields["article10_order_authority"] = dict(case.config["article10_order_authority"])
        res.fields["order_used"] = order
        sequence = _activate_body_plan(res, "PARTIAL_DAMAGE", branch_plan, sequence)
        res.payable = graph_partial_payable(
            after_depreciation, franchise, ratio, rescue, sequence
        )
        return

    scenario_sequences = _activate_body_plan(
        res, "PARTIAL_DAMAGE", branch_plan, sequences_with_ratio(branch_plan)
    )
    scenario_amounts = [
        graph_partial_payable(after_depreciation, franchise, ratio, rescue, item)
        for item in scenario_sequences
    ]
    if len(scenario_amounts) != 2:
        raise PlanError("partial-damage plan must provide both operator-order scenarios")
    res.fields["scenario_ratio_then_franchise"] = scenario_amounts[0]
    res.fields["scenario_franchise_then_ratio"] = scenario_amounts[1]
    res.payable_scenarios = scenario_amounts
    res.payable = None
    res.status = "ORDER_UNRESOLVED"
    res.reason = "supply applicable legal or contractual authority establishing the operator sequence; " + (order_gap or "the selected order is unresolved")
    res.fields["order_used"] = UNRESOLVED_ORDER
    res.block("U01_ARTICLE10_PARTIAL_ORDER")
    res.label("ORDER_UNRESOLVED")


# ---------------------------------------------------------------- total loss


def _settle_total_loss(case: Case, kb: Knowledge, res: CalcResult) -> None:
    market = case.market_value
    insured = case.insured_sum
    if market is None or insured is None:
        raise operators.OperatorError(
            "market value and insured sum are both required for a total-loss settlement"
        )

    base = min(market, insured)
    res.fields["settlement_base"] = base
    active = kb.branch(res.branch or "TOTAL_LOSS") or {}
    res.note_rule("REG53_ART19_TOTAL_LOSS_VALUATION")

    if insured < market:
        res.fields["underinsurance_ratio_equivalent"] = insured / market
        res.fields["guard_ratio_twice"] = "PROHIBITED"
        res.note_rule("REG53_ART19_TOTAL_LOSS_NO_DOUBLE_UNDERINSURANCE")
        res.label("DO_NOT_APPLY_RATIO_TWICE")
    res.note_guard("G_NO_DOUBLE_UNDERINSURANCE_IN_TOTAL_LOSS")

    # Whole theft has already passed its separate transfer condition. It has no
    # retained wreck valuation; physical-loss completeness must not invent one.
    disposition = (
        "INSURER_TAKES_TITLE"
        if res.route == "THEFT_TOTAL_SETTLEMENT"
        else case.salvage_disposition
    )
    if disposition not in ("INSURED_RETAINS", "INSURER_TAKES_TITLE"):
        raise operators.UncertaintyRequired(
            "U12_SALVAGE_DISPOSITION",
            "salvage disposition is unresolved, so the settlement base cannot be fixed",
            status="SALVAGE_DISPOSITION_UNRESOLVED",
        )

    res.require_guard("G_SALVAGE_XOR_TITLE_TRANSFER")
    if disposition == "INSURER_TAKES_TITLE":
        if not case.title_transferred or case.evidence.get("EVT_TITLE_TRANSFER_PROOF") is not True:
            raise guards.GuardViolation(
                "G_SALVAGE_XOR_TITLE_TRANSFER",
                (
                    "the insurer-title settlement route requires completed title transfer "
                    "before salvage can be omitted"
                ),
                "TITLE_TRANSFER_REQUIRED",
            )
        salvage_to_deduct = Decimal(0)
        after_salvage = base
        res.fields["salvage_deduction"] = Decimal(0)
        res.fields["salvage_disposition"] = disposition
        res.note_rule("REG53_ART19_INSURER_TAKES_TITLE")
        res.label("DO_NOT_DEDUCT_SALVAGE_AND_TRANSFER_IT")
    else:
        if case.salvage is None:
            raise guards.GuardViolation(
                "G_SALVAGE_XOR_TITLE_TRANSFER",
                "retained salvage requires an established valuation; absence is not zero",
                "SALVAGE_VALUE_REQUIRED",
            )
        if case.evidence.get("EVT_SALVAGE_VALUATION") is not True:
            raise guards.GuardViolation(
                "G_SALVAGE_XOR_TITLE_TRANSFER",
                "retained salvage valuation requires supporting assessment evidence",
                "SALVAGE_VALUATION_EVIDENCE_REQUIRED",
            )
        salvage_to_deduct = case.salvage
        after_salvage = base - salvage_to_deduct
        res.fields["salvage_deduction"] = salvage_to_deduct
        res.fields["salvage_disposition"] = disposition
        if salvage_to_deduct > 0:
            res.note_rule("CIC_CIRC_1400_401_146850_SALVAGE_BEFORE_FRANCHISE")
            res.label("SALVAGE_DEDUCTED_BEFORE_FRANCHISE")
    res.note_guard("G_SALVAGE_XOR_TITLE_TRANSFER")
    res.fields["base_after_salvage"] = after_salvage

    repair = case.repair_total
    rescue = _rescue(
        case,
        res,
        {
            "ASSESSED_GROSS": repair if repair is not None else base,
            "ELIGIBLE_GROSS": base,
            "SETTLEMENT_BASE": base,
        },
    )
    franchise = _resolve_franchise(
        case,
        res,
        {
            "AFTER_SALVAGE": after_salvage,
            "SETTLEMENT_BASE": base,
            "GROSS_ELIGIBLE": base,
        },
    )

    sequence = _activate_body_plan(
        res,
        res.branch or "TOTAL_LOSS",
        active,
        list(active.get("operators") or []),
    )
    result_before_cap = graph_total_loss_payable(
        base,
        salvage_to_deduct,
        franchise,
        rescue,
        Decimal("Infinity"),
        sequence,
    )
    res.payable = graph_total_loss_payable(
        base,
        salvage_to_deduct,
        franchise,
        rescue,
        insured,
        sequence,
    )
    if res.payable != max(Decimal(0), result_before_cap):
        res.label("INSURED_SUM_CEILING_APPLIED")
    res.note_guard("G_INSURED_SUM_CEILING")


def calculate_total_loss(case: Case, kb: Knowledge, res: CalcResult) -> None:
    res.label("TOTAL_LOSS")
    market = case.market_value
    repair = case.repair_total
    classification_rescue, rescue_source, unresolved = case.classification_rescue()
    if unresolved is not None:
        raise ClassificationEvidenceRequired(unresolved)
    is_total, combined, threshold = operators.is_total_loss(
        repair, classification_rescue, market
    )
    if combined is not None:
        res.fields["classification_rescue"] = classification_rescue
        res.fields["classification_rescue_source"] = rescue_source
        res.fields["combined_for_threshold"] = combined
        res.fields["threshold_value"] = threshold
        res.fields["threshold_ratio"] = combined / market if market else None
        res.fields["is_total"] = is_total
        res.note_rule("REG53_ART19_TOTAL_LOSS_THRESHOLD")

    authorized_override = (
        res.fields.get("classification", {}).get("outcome") == "AUTHORIZED_OVERRIDE"
    )
    if is_total is False and not authorized_override:
        res.payable = None
        if threshold is not None and combined == threshold:
            res.reason = "EXACTLY_75_PERCENT_IS_NOT_MORE_THAN_75_PERCENT"
            res.label("THRESHOLD_EQUALITY_NOT_TOTAL_LOSS")
        else:
            res.reason = "NOT_TOTAL_LOSS"
            res.label("NOT_TOTAL_LOSS")
        return

    if authorized_override:
        res.fields["total_loss_threshold_override"] = True

    if res.variant == "THRESHOLD_TEST":
        res.fields["is_total"] = is_total
        res.payable = None
        return

    _settle_total_loss(case, kb, res)


# --------------------------------------------------------------------- glass


def calculate_glass(case: Case, kb: Knowledge, res: CalcResult) -> None:
    res.label("GLASS_ONLY")
    res.require_guard("G_NO_UNIVERSAL_GLASS_FRANCHISE")
    guards.check_universal_glass_franchise(case)
    res.note_guard("G_NO_UNIVERSAL_GLASS_FRANCHISE")

    if case.glass_damage_from_base_peril:
        res.route = "PARTIAL_DAMAGE"
        res.label("ROUTED_TO_PARTIAL_DAMAGE")
        calculate_partial_damage(case, kb, res)
        return

    if not case.has_glass_endorsement:
        res.payable = money.D(0)
        res.reason = "NO_STANDALONE_COVER"
        res.fields["endorsement_required"] = "GLASS_ONLY"
        res.note_rule("REG53_ART5_ENDORSABLE_EXCLUSIONS", "REG53_POLICY_DEFINED_FRANCHISE")
        res.label("NO_STANDALONE_COVER")
        return

    res.note_rule("REG53_ART19_GLASS_DEPRECIATION_EXEMPTION")

    parts = case.parts
    if parts:
        gross = sum((money.D(part["assessed_loss"]) for part in parts), Decimal(0)) + (
            case.labor or Decimal(0)
        )
    else:
        gross = case.gross_damage if case.gross_damage is not None else (case.labor or Decimal(0))

    res.fields["gross_eligible"] = gross
    res.fields["depreciation"] = Decimal(0)
    res.fields["glass_depreciation"] = Decimal(0)
    res.fields["depreciation_source"] = "GLASS_EXEMPT_BY_RULE"

    rescue = _rescue(
        case,
        res,
        {
            "ASSESSED_GROSS": gross,
            "ELIGIBLE_GROSS": gross,
            "SETTLEMENT_BASE": gross,
        },
    )
    franchise = _resolve_franchise(
        case,
        res,
        {
            "ASSESSED_GROSS": gross,
            "GROSS_ELIGIBLE": gross,
            "AFTER_DEPRECIATION": gross,
            "SETTLEMENT_BASE": gross,
        },
    )
    ratio = _ratio(case, res)
    res.note_guard("G_GLASS_ARTICLE10_NOT_AUTO_EXEMPT")
    order = str(case.config.get("article10_partial_order", UNRESOLVED_ORDER)).upper()
    contractually_resolved = bool(case.config.get("glass_article10_order_resolved_by_endorsement"))

    glass_plan = kb.branch("GLASS_ONLY") or {}
    if ratio == 1:
        res.fields["order_used"] = "RATIO_NOT_APPLICABLE"
        sequence = _activate_body_plan(
            res,
            "GLASS_ONLY",
            glass_plan,
            list(glass_plan.get("operators") or []),
        )
        res.payable = graph_partial_payable(gross, franchise, ratio, rescue, sequence)
        return

    if contractually_resolved and order in RESOLVED_PARTIAL_ORDERS:
        ratio_before = order == "AFTER_DEPRECIATION_BEFORE_FRANCHISE"
        sequence = next(
            (
                item
                for item in sequences_with_ratio(glass_plan)
                if (item.index(RATIO) < item.index(FRANCHISE)) == ratio_before
            ),
            None,
        )
        if sequence is not None:
            res.fields["order_used"] = order
            sequence = _activate_body_plan(res, "GLASS_ONLY", glass_plan, sequence)
            res.payable = graph_partial_payable(gross, franchise, ratio, rescue, sequence)
            return

    scenario_sequences = _activate_body_plan(
        res, "GLASS_ONLY", glass_plan, sequences_with_ratio(glass_plan)
    )
    scenario_amounts = [
        graph_partial_payable(gross, franchise, ratio, rescue, item)
        for item in scenario_sequences
    ]
    if len(scenario_amounts) != 2:
        raise PlanError("glass plan must provide both operator-order scenarios")
    ratio_first, franchise_first = scenario_amounts
    res.fields["scenario_ratio_then_franchise"] = ratio_first
    res.fields["scenario_franchise_then_ratio"] = franchise_first
    res.payable_scenarios = [ratio_first, franchise_first]
    res.payable = None
    res.status = "ENDORSEMENT_AND_ORDER_REQUIRED"
    res.block("U03_GLASS_ONLY_ENDORSEMENT_WORDING", "U11_GLASS_ARTICLE10_EXEMPTION")
    res.label("GLASS_UNDERINSURANCE_UNRESOLVED")


# --------------------------------------------------------------------- theft


# Borkowski/Jalaali break table, used by the established deterministic
# JalCal algorithm. The bounded range is deliberate: an unsupported year must
# fail closed instead of silently switching to an approximate 33-year cycle.
def _is_shamsi_leap_year(year: int) -> bool:
    """Return JalCal's leap-year result for a supported Shamsi year."""
    try:
        return is_shamsi_leap_year(year)
    except CalendarDateError as error:
        raise operators.OperatorError(
            f"unsupported SHAMSI theft-clock year {year!r}"
        ) from error


def _shamsi_ordinal(value: str) -> int:
    """Return a consistent day ordinal after validating a Shamsi date."""
    try:
        return parse_claim_date(value, calendar="SHAMSI").chronology_key
    except CalendarDateError as error:
        raise operators.OperatorError(
            f"invalid SHAMSI theft-clock date {value!r}"
        ) from error


def _dated_theft_clock_days(clock: dict[str, Any]) -> int:
    """Derive an elapsed whole-day count from a bound calendar snapshot."""

    start = str(clock.get("start_date") or "")
    as_of = str(clock.get("as_of_date") or "")
    calendar = str(clock.get("calendar") or "").upper()
    try:
        start_date = parse_claim_date(start, calendar=calendar)
        as_of_date = parse_claim_date(as_of, calendar=calendar)
        elapsed = as_of_date.chronology_key - start_date.chronology_key
    except CalendarDateError as error:
        if calendar not in ("GREGORIAN", "SHAMSI"):
            raise operators.OperatorError(
                f"unsupported theft-clock calendar {calendar!r}"
            ) from error
        label = "Gregorian" if calendar == "GREGORIAN" else "SHAMSI"
        raise operators.OperatorError(
            f"invalid {label} theft-clock date: {error}"
        ) from error
    if elapsed < 0:
        raise operators.OperatorError("theft-clock as_of_date precedes its start_date")
    return elapsed


_THEFT_CLOCK_EVENT_DATE_FIELDS = {
    "THEFT_OCCURRENCE": "event_date",
    "AWARENESS": "awareness_date",
    "DECLARATION": "declaration_date",
}


def _validate_theft_clock_start_event(case: Case, clock: dict[str, Any]) -> None:
    """Bind the selected clock event to its canonical date in the case file."""

    start_event = str(clock.get("start_event") or "")
    event_date_field = _THEFT_CLOCK_EVENT_DATE_FIELDS.get(start_event)
    if event_date_field is None:
        raise operators.OperatorError(
            f"unsupported theft-clock start_event {start_event!r}"
        )

    event_date = case.event.get(event_date_field)
    if not isinstance(event_date, str) or not event_date:
        raise operators.UncertaintyRequired(
            "U13_THEFT_CLOCK_ANCHOR",
            f"theft-clock start_event {start_event} requires event.{event_date_field}",
            status="THEFT_CLOCK_ANCHOR_UNRESOLVED",
        )

    start_date = str(clock.get("start_date") or "")
    try:
        start_key = parse_claim_date(
            start_date, calendar=str(clock.get("calendar") or "")
        ).chronology_key
        event_key = parse_claim_date(event_date).chronology_key
    except CalendarDateError as error:
        raise operators.OperatorError(
            "theft-clock start event contains an invalid calendar date"
        ) from error
    if start_key != event_key:
        raise operators.OperatorError(
            f"theft-clock start_date ({start_date}) does not match "
            f"event.{event_date_field} ({event_date}) for {start_event}"
        )


def calculate_theft(case: Case, kb: Knowledge, res: CalcResult) -> None:
    res.label("THEFT")
    theft_type = case.theft_type
    if theft_type is None and res.variant == "TOTAL_SETTLEMENT":
        theft_type = "WHOLE_VEHICLE"
    if theft_type is None:
        raise operators.OperatorError("theft_type is required for a theft claim")

    if theft_type == "WHOLE_VEHICLE":
        days = case.days_missing
        if days is None:
            raise operators.OperatorError("days_vehicle_missing is required for whole-vehicle theft")
        clock = case.theft_clock
        if clock is None:
            raise operators.UncertaintyRequired(
                "U13_THEFT_CLOCK_ANCHOR",
                "whole-vehicle theft needs a sourced start event, start date and as-of date",
                status="THEFT_CLOCK_ANCHOR_UNRESOLVED",
            )
        _validate_theft_clock_start_event(case, clock)
        derived_days = _dated_theft_clock_days(clock)
        if derived_days != days:
            raise operators.OperatorError(
                f"days_vehicle_missing ({days}) does not match the bound theft clock ({derived_days})"
            )
        res.fields["theft_clock"] = {
            "start_event": clock["start_event"],
            "start_date": clock["start_date"],
            "as_of_date": clock["as_of_date"],
            "calendar": clock["calendar"],
            "source": clock["source"],
            "derived_days": derived_days,
        }
        res.fields["days_missing"] = days
        res.note_rule("REG53_ART19_THEFT_TOTAL_LOSS_60D")
        if days < 60:
            res.payable = None
            if res.variant == "TOTAL_SETTLEMENT":
                res.status = "60_DAY_TOTAL_LOSS_CRITERION_NOT_MET"
            else:
                res.status = "PENDING_60_DAY_CRITERION"
            res.fields["total_loss_criterion"] = False
            res.label(res.status)
            return
        if not case.title_transferred:
            res.payable = None
            res.status = "TITLE_TRANSFER_REQUIRED"
            res.label("TITLE_TRANSFER_REQUIRED")
            return
        res.route = "THEFT_TOTAL_SETTLEMENT"
        res.fields["total_loss_criterion"] = True
        res.label("TITLE_TRANSFERRED_TO_INSURER")
        _settle_total_loss(case, kb, res)
        return

    if theft_type == "ATTEMPTED_VEHICLE_THEFT_DAMAGE":
        res.route = "THEFT_PARTIAL_DAMAGE"
        calculate_partial_damage(case, kb, res)
        return

    if theft_type in ("PARTIAL_PARTS_THEFT", "PARTS_STOLEN_AFTER_ACCIDENT"):
        res.payable = None
        res.status = "ENDORSEMENT_LIMIT_AND_FRANCHISE_REQUIRED"
        res.fields["endorsement_required"] = "PARTIAL_THEFT"
        res.label("ENDORSEMENT_TERMS_REQUIRED")
        res.block("U02_FRANCHISE_BASE_SCHEDULES")
        return

    raise operators.OperatorError(f"unsupported theft_type {theft_type!r}")


# ------------------------------------------------------- third party financial


def calculate_third_party(case: Case, kb: Knowledge, res: CalcResult) -> None:
    res.label("THIRD_PARTY_FINANCIAL")
    actual = case.actual_damage
    if actual is None:
        raise operators.OperatorError("actual_financial_loss is required")
    limit = case.financial_limit
    if limit is None:
        raise operators.OperatorError("the third-party policy financial limit is required")

    if case.property_type != "PASSENGER_VEHICLE":
        res.fields["property_type"] = case.property_type
        res.fields["article8_vehicle_cap"] = "NOT_APPLICABLE"
        res.fields["insurer_payable"] = min(actual, limit)
        if actual > limit:
            res.fields["remaining_legal_claim_candidate"] = actual - limit
        res.payable = min(actual, limit)
        res.note_rule("TPL_LAW_1395_ART8_MIN_FINANCIAL_COMMITMENT")
        return

    value = case.victim_vehicle_value
    if value is None:
        raise operators.OperatorError("the damaged passenger car's value is required")
    threshold = _threshold(case, kb)
    if threshold is None:
        raise operators.OperatorError(
            "the annual conventional-vehicle threshold is required to classify the damaged car"
        )

    if value < threshold:
        res.fields["vehicle_class"] = "CONVENTIONAL"
        res.fields["threshold_used"] = threshold
        res.fields["insurer_payable"] = min(actual, limit)
        if actual > limit:
            res.fields["remaining_legal_claim_candidate"] = actual - limit
        res.payable = min(actual, limit)
        res.note_rule("HIC_ARTICLE8_CONVENTIONAL_DEFINITION")
        return

    res.fields["vehicle_class"] = "NON_CONVENTIONAL"
    res.fields["threshold_used"] = threshold
    res.note_rule("HIC_ARTICLE8_CONVENTIONAL_DEFINITION")
    res.route = "ARTICLE_8"
    calculate_article8(case, kb, res)


def calculate_article8(case: Case, kb: Knowledge, res: CalcResult) -> None:
    res.label("ARTICLE_8_NON_CONVENTIONAL")
    res.require_guard("G_ARTICLE8_NO_WHOLE_CAR_RATIO")
    guards.check_article8_method(case)
    res.note_guard("G_ARTICLE8_NO_WHOLE_CAR_RATIO")

    corresponding = case.corresponding_damage
    if corresponding is None:
        raise operators.UncertaintyRequired(
            "U06_ARTICLE8_COMPONENT_CATALOGUE",
            (
                "no corresponding-damage assessment was supplied; the amended instruction "
                "delegates the component valuation map to adjusters, and the engine will not "
                "manufacture it from a vehicle-value ratio"
            ),
        )
    limit = case.financial_limit
    if limit is None:
        raise operators.OperatorError("the third-party policy financial limit is required")

    actual = case.actual_damage
    if actual is None:
        actual = corresponding
    insurer_payable = min(actual, corresponding, limit)
    excess = max(Decimal(0), actual - corresponding)

    res.fields["actual_damage"] = actual
    res.fields["corresponding_damage"] = corresponding
    res.fields["insurer_payable"] = insurer_payable
    res.fields["tp_insurer_payable"] = insurer_payable
    damage_inside_article8_cap = min(actual, corresponding)
    res.fields["remaining_inside_article8_cap"] = max(
        Decimal(0), damage_inside_article8_cap - insurer_payable
    )
    res.fields["non_corresponding_excess"] = excess
    res.fields["own_body_excess_candidate"] = excess
    res.fields["own_body_non_corresponding_excess_candidate"] = excess
    res.note_rule(
        "HIC_ARTICLE8_CORRESPONDING_DAMAGE", "TPL_LAW_1395_ART8_NON_CONVENTIONAL_LIMIT"
    )
    res.require_guard("G_DUAL_LIABILITY_CAP")
    if insurer_payable < corresponding:
        res.label("DUAL_CAP_APPLIED")
    res.note_guard("G_DUAL_LIABILITY_CAP")

    if res.variant == "DUAL_COVERAGE":
        res.fields["third_party"] = insurer_payable
        res.note_rule("CIC_CIRC_1404_06_10_ARTICLE8_EXCESS_OWN_BODY")
        if case.has_body_policy:
            res.require_guard("G_NO_MANDATORY_FRANCHISE_WITHOUT_DISCLOSURE")
            if case.body_franchise_for_excess_disclosed:
                res.fields["body_candidate_before_disclosed_terms"] = excess
                res.label("APPLY_VALID_DISCLOSED_POLICY_TERM")
            else:
                res.fields["body_candidate_before_other_body_terms"] = excess
                res.fields["regulatory_mandatory_franchise_on_this_excess"] = money.D(0)
                res.note_rule("CIC_CIRC_1404_06_10_NO_MANDATORY_FRANCHISE_ON_ART8_EXCESS")
            res.note_guard("G_NO_MANDATORY_FRANCHISE_WITHOUT_DISCLOSURE")
        res.payable = insurer_payable
        return

    if case.has_body_policy is False:
        res.fields["tp_or_at_fault_statutory_cap"] = corresponding
        res.fields["non_corresponding_residual"] = excess
        res.label("AT_FAULT_CAP_APPLIED")
        res.note_rule("TPL_LAW_1395_ART8_AT_FAULT_CAP")
        res.payable = insurer_payable
        return

    res.payable = insurer_payable


# -------------------------------------------------------------- legal recovery


def calculate_legal_recovery(case: Case, kb: Knowledge, res: CalcResult) -> None:
    res.label("LEGAL_RECOVERY")
    res.note_rule("REG53_ART14_SUBROGATION")

    if case.recovery_right_impaired or case.insured_released_responsible_party:
        res.payable = None
        res.status = "ARTICLE_14_SUBROGATION_IMPAIRMENT_REVIEW"
        res.label("SUBROGATION_IMPAIRMENT_REVIEW")
        return

    paid = case.body_insurer_paid
    if paid is None:
        raise operators.OperatorError("body_insurer_paid is required for a subrogation calculation")

    cap = case.corresponding_damage or case.actual_damage
    ceiling = min(paid, cap) if cap is not None else paid
    res.fields["body_insurer_paid"] = paid
    res.fields["insurer_subrogation_ceiling"] = ceiling
    if cap is not None:
        res.note_rule("TPL_LAW_1395_ART8_AT_FAULT_CAP")
    res.payable = ceiling
    res.status = "INSURER_MAY_PURSUE_RESPONSIBLE_PARTY"
    res.fields["subrogation_holder"] = "BODY_INSURER"


DISPATCH: dict[str, Callable[[Case, Knowledge, CalcResult], None]] = {
    "PARTIAL_DAMAGE": calculate_partial_damage,
    "TOTAL_LOSS": calculate_total_loss,
    "GLASS_ONLY": calculate_glass,
    "THEFT": calculate_theft,
    "THIRD_PARTY_FINANCIAL": calculate_third_party,
    "ARTICLE_8_NON_CONVENTIONAL": calculate_article8,
    "LEGAL_RECOVERY": calculate_legal_recovery,
}

BODY_BRANCHES = {"PARTIAL_DAMAGE", "TOTAL_LOSS", "GLASS_ONLY", "THEFT"}
RESCUE_THRESHOLD_BRANCHES = {"PARTIAL_DAMAGE", "TOTAL_LOSS", "GLASS_ONLY"}


def _classification_evidence_gap(
    case: Case, declared: str | None, derived: str
) -> str | None:
    if declared == "TOTAL_LOSS" and derived == "PARTIAL_DAMAGE":
        missing = []
        if case.repair_total is None:
            missing.append("repair-and-replacement assessment")
        if case.market_value is None:
            missing.append("event-date market value")
        if missing:
            return "total-loss classification needs " + " and ".join(missing)
    if declared == "THEFT" and case.theft_type is None and case.variant != "TOTAL_SETTLEMENT":
        return "theft classification needs the theft type"
    if (
        declared == "GLASS_ONLY"
        and derived == "PARTIAL_DAMAGE"
        and not case.has_glass_endorsement
        and not case.cause
        and not case.peril
    ):
        return "glass-only classification needs cause or endorsement evidence"
    return None


def _missing_classification_rescue_reason() -> str:
    return (
        "classification rescue is missing; a non-negative amount could change the "
        "strict 75% branch or the settlement, so the preliminary zero cannot authorize "
        "payment and this evidence gate cannot be overridden"
    )


def _final_selected_branch_evidence_gap(
    case: Case, selected_branch: str | None
) -> str | None:
    """Require the classification operands consumed by an override-selected route.

    An override supplies authority to select a branch; it does not supply the
    evidence that branch needs. Threshold-dependent body routes therefore need
    their repair, market and classification-rescue operands before the override
    can become calculation authorization.
    """
    if selected_branch not in RESCUE_THRESHOLD_BRANCHES:
        return None

    missing = []
    if case.repair_total is None:
        missing.append("repair-and-replacement assessment")
    if case.market_value is None:
        missing.append("event-date market value")

    classification_rescue, rescue_source, unresolved_rescue = (
        case.classification_rescue()
    )
    if unresolved_rescue is not None:
        return unresolved_rescue
    if classification_rescue is None and (
        rescue_source == "UNRESOLVED_MISSING_RESCUE"
    ):
        missing.append("classification rescue")

    if not missing:
        return None
    if missing == ["classification rescue"]:
        return _missing_classification_rescue_reason()
    return (
        f"override-selected {selected_branch} classification needs "
        + ", ".join(missing)
    )


def reconcile_classification(
    case: Case, kb: Knowledge
) -> tuple[dict[str, Any], str | None, str | None]:
    try:
        verdict = classify(case, kb)
    except ClassificationEvidenceRequired as error:
        reason = str(error)
        return (
            {
                "declared_branch": case.declared_branch,
                "declared_canonical_branch": case.branch,
                "derived_branch": None,
                "outcome": "INSUFFICIENT_EVIDENCE",
                "confidence": 0.0,
                "basis": [reason],
                "reason": reason,
            },
            None,
            reason,
        )
    derived = verdict["branch"]
    declared = case.branch
    classification_rescue, rescue_source, unresolved_rescue = (
        case.classification_rescue()
    )
    override = case.classification_override
    # Candidate branches selected by an override are checked independently by
    # _final_selected_branch_evidence_gap. Keep this predicate about the
    # evidence-derived route so the two gates do not encode the same condition.
    threshold_classification_participates = derived in RESCUE_THRESHOLD_BRANCHES
    unresolved_rescue_gate = (
        unresolved_rescue is not None
        and (declared == "TOTAL_LOSS" or threshold_classification_participates)
    ) or (
        threshold_classification_participates
        and case.repair_total is not None
        and case.market_value is not None
        and classification_rescue is None
        and rescue_source == "UNRESOLVED_MISSING_RESCUE"
    )
    final_selected_branch_gap = (
        _final_selected_branch_evidence_gap(case, declared)
        if override is not None and not unresolved_rescue_gate
        else None
    )
    if unresolved_rescue_gate:
        gap = unresolved_rescue or _missing_classification_rescue_reason()
    elif final_selected_branch_gap is not None:
        gap = final_selected_branch_gap
    else:
        gap = _classification_evidence_gap(case, declared, derived)

    if gap:
        outcome = "INSUFFICIENT_EVIDENCE"
        selected = None
        reason = gap
    elif declared is None:
        outcome = "MATCH"
        selected = derived
        reason = "no branch was declared; the evidence-derived branch is authoritative"
    elif declared == derived:
        outcome = "MATCH"
        selected = declared
        reason = "declared and evidence-derived branches agree"
    else:
        outcome = "CONFLICT"
        selected = None
        reason = f"declared {declared} conflicts with evidence-derived {derived}"

    if (
        outcome in ("CONFLICT", "INSUFFICIENT_EVIDENCE")
        and override is not None
        and not unresolved_rescue_gate
        and final_selected_branch_gap is None
    ):
        outcome = "AUTHORIZED_OVERRIDE"
        selected = declared
        reason = "documented classification override authorizes the declared branch"

    record: dict[str, Any] = {
        "declared_branch": case.declared_branch,
        "declared_canonical_branch": declared,
        "derived_branch": derived,
        "outcome": outcome,
        "confidence": verdict["confidence"],
        "basis": verdict["basis"],
        "reason": reason,
    }
    if override is not None:
        record["override"] = override
    return record, selected, gap


# --------------------------------------------------------------------- driver


def _finalize(res: CalcResult, kb: Knowledge, case: Case) -> None:
    confidences: list[float] = []
    provenance: list[dict[str, Any]] = []
    findings: list[str] = []
    plan = _flat_plan(res.fields.get("execution_plan"))
    for rule_id in res.rule_trace:
        rule = kb.rule(rule_id)
        if rule is None:
            findings.append(f"rule {rule_id} is missing from the graph")
        else:
            confidences.append(float(rule.get("confidence", 0.0)))
            if not rule.get("sources"):
                findings.append(f"rule {rule_id} has no source")
        operators_for_rule = [
            operator_id
            for operator_id, operator in kb.operators.items()
            if rule_id in (operator.get("sourced_from") or [])
        ]
        on_plan = (
            [operator_id for operator_id in operators_for_rule if operator_id in plan]
            if plan
            else operators_for_rule
        )
        entry = kb.provenance(rule_id)
        entry["source"] = list(entry.get("sources") or [])
        entry["rule"] = rule_id
        entry["operator"] = on_plan
        entry["execution"] = {
            "snapshot_id": res.fields.get("snapshot_id"),
            "plan": plan,
        }
        provenance.append(entry)
    for uncertainty_id in res.blocking_uncertainties:
        uncertainty = kb.uncertainty(uncertainty_id)
        confidence = None if uncertainty is None else uncertainty.get(
            "confidence_of_single_interpretation"
        )
        if confidence is not None:
            confidences.append(float(confidence))
    res.formula_confidence = min(confidences) if confidences else None
    required = list((kb.branch(res.branch or "") or {}).get("required_evidence") or [])
    evidence = case.evidence if isinstance(case.evidence, dict) else {}
    supplied = {key for key, value in evidence.items() if value is True}
    missing = [item for item in required if item not in supplied]
    if missing or not required:
        res.evidence_confidence = None
        if missing:
            findings.append("evidence missing: " + ", ".join(missing))
        elif res.branch in BODY_BRANCHES and not required:
            findings.append("body branch declares no required evidence")
    else:
        res.evidence_confidence = 1.0
    if findings:
        res.fields["provenance_findings"] = findings
    if res.blocking_uncertainties:
        res.label("BLOCKING_UNCERTAINTY_SURFACED")
    if res.payable is not None:
        res.payable = money.round_irr(res.payable)
    res.payable_scenarios = [money.round_irr(value) for value in res.payable_scenarios]
    for entry in provenance:
        entry["result"] = res.payable
    res.provenance = provenance


def _apply_authorization_confidence_cap(res: CalcResult) -> None:
    """Apply an evidence cap bound into immutable review provenance.

    CLI callers invoke ``Review.authorize()`` followed directly by ``compute()``.
    Enforcing the cap here keeps that supported path identical to
    ``Review.calculate()`` and prevents callers from bypassing a review-issued
    evidence constraint.
    """
    raw_cap = res.authorization.get("evidence_confidence_cap")
    if raw_cap is None or res.formula_confidence is None:
        return
    cap = money.D(raw_cap)
    current = money.D(str(res.formula_confidence))
    if cap < current:
        res.formula_confidence = float(cap)
        res.label("EVIDENCE_CONFIDENCE_REDUCED")


def _reconcile_authorization_uncertainties(res: CalcResult) -> None:
    """Keep review-live uncertainties visible at the calculation boundary.

    A review authorization is an immutable statement of what remained open.
    The engine may reproduce those uncertainties, but it may not silently lose
    one and emit a deterministic payable. Any authorization uncertainty not
    already surfaced by runtime is therefore added as a blocking result.
    """
    authorized = [
        str(item)
        for item in (res.authorization.get("live_uncertainties") or [])
        if item
    ]
    res.fields["authorization_live_uncertainties"] = authorized
    missing = [item for item in authorized if item not in res.blocking_uncertainties]
    if not missing:
        return
    for uncertainty_id in missing:
        res.block(uncertainty_id)
    res.fields["authorization_uncertainties_added"] = missing
    res.payable = None
    res.payable_scenarios = []
    res.status = "AUTHORIZED_UNCERTAINTY_UNRESOLVED"
    res.reason = "review-live uncertainty was not resolved by a bound calculation artefact"
    res.label("AUTHORIZATION_UNCERTAINTY_RECONCILED")


def _flat_plan(plan: Any) -> list[str]:
    if not isinstance(plan, list):
        return []
    flat: list[str] = []
    for item in plan:
        if isinstance(item, list):
            flat.extend(str(step) for step in item)
        else:
            flat.append(str(item))
    return flat


def _bind_body_snapshot(case: Case, kb: Knowledge, res: CalcResult) -> bool:
    """event date → snapshot. Operators run only after this identity exists."""
    snapshot = kb.resolve_snapshot(case.event_date, case.claim_year)
    if snapshot is None:
        res.payable = None
        res.status = "INSUFFICIENT_INFORMATION"
        res.reason = "no regulatory snapshot resolves for the event date"
        res.label("INSUFFICIENT_INFORMATION")
        return False
    res.fields["snapshot_id"] = snapshot["snapshot_id"]
    res.fields["snapshot_rule_ids"] = snapshot["rule_ids"]
    return True


def compute(
    authorization: CalculationAuthorization,
    kb: Knowledge | None = None,
) -> CalcResult:
    """Run one authorized claim.

    ``authorization`` is the only admissible input: a raw case payload or a
    ``Case`` cannot reach the engine without some issuer admitting it first.
    The authorization owns the exact validated payload as immutable canonical
    JSON. A fresh ``Case`` is materialized only after verification, so mutable
    objects that existed before issuance cannot affect this calculation.
    """
    if not isinstance(authorization, CalculationAuthorization):
        raise AuthorizationError(
            "compute() requires a CalculationAuthorization issued by Review.authorize(); "
            "run the claim through the review gate before calculation"
        )
    authorization.verify()
    case = validated_case(authorization.claim_payload())
    kb = kb or Knowledge.load()

    res = CalcResult(
        branch=case.branch,
        variant=case.variant,
        domain=case.domain,
        claim_id=case.claim_id,
        unit=case.unit,
        authorization=authorization.provenance_record(),
    )

    reconcile_body = res.branch in BODY_BRANCHES or (
        res.branch is None and res.domain != "LEGAL_RECOVERY"
    )
    if reconcile_body:
        reconciliation, selected, _ = reconcile_classification(case, kb)
        res.fields["classification"] = reconciliation
        if case.repair_total is not None and case.market_value is not None:
            res.note_rule("REG53_ART19_TOTAL_LOSS_THRESHOLD")
            classification_rescue, rescue_source, unresolved_rescue = (
                case.classification_rescue()
            )
            if unresolved_rescue is None:
                res.fields["classification_rescue"] = classification_rescue
                res.fields["classification_rescue_source"] = rescue_source
        if reconciliation["outcome"] == "CONFLICT":
            res.payable = None
            res.status = "CLASSIFICATION_CONFLICT"
            res.reason = reconciliation["reason"]
            res.label("CLASSIFICATION_CONFLICT")
        elif reconciliation["outcome"] == "INSUFFICIENT_EVIDENCE":
            res.payable = None
            res.status = "CLASSIFICATION_EVIDENCE_REQUIRED"
            res.reason = reconciliation["reason"]
            res.label("CLASSIFICATION_EVIDENCE_REQUIRED")
        else:
            res.branch = selected
            if case.declared_branch is None:
                guessed = classify(case, kb)
                res.variant = guessed["variant"]
            res.domain = res.domain or DOMAIN_BY_BRANCH.get(res.branch)
            if reconciliation["outcome"] == "AUTHORIZED_OVERRIDE":
                res.label("AUTHORIZED_CLASSIFICATION_OVERRIDE")
    elif res.branch is None:
        guessed = classify(case, kb)
        res.branch = guessed["branch"]
        res.variant = guessed["variant"]
        res.domain = res.domain or DOMAIN_BY_BRANCH.get(guessed["branch"])
        res.fields["classification"] = {
            "declared_branch": None,
            "declared_canonical_branch": None,
            "derived_branch": guessed["branch"],
            "outcome": "MATCH",
            "confidence": guessed["confidence"],
            "basis": guessed["basis"],
            "reason": "no branch was declared; the evidence-derived branch is authoritative",
        }

    try:
        classification_blocked = res.status in (
            "CLASSIFICATION_CONFLICT",
            "CLASSIFICATION_EVIDENCE_REQUIRED",
        )
        if (
            not classification_blocked
            and res.branch in BODY_BRANCHES
            and not _bind_body_snapshot(case, kb, res)
        ):
            classification_blocked = True
        if not classification_blocked and res.branch in BODY_BRANCHES:
            enforce_body_eligibility_admission(case, res)
        if not classification_blocked and not evaluate_coverage_gate(case, kb, res):
            if res.branch in BODY_BRANCHES:
                check_risk_intensification(case, kb)
            handler = DISPATCH.get(res.branch)
            if handler is None:
                res.payable = None
                res.status = "UNKNOWN_BRANCH"
                res.reason = f"no branch engine is registered for {res.branch!r}"
            else:
                handler(case, kb, res)
    except operators.UncertaintyRequired as uncertainty:
        res.payable = None
        res.status = res.status or uncertainty.status or uncertainty.uncertainty_id
        res.block(uncertainty.uncertainty_id)
        res.fields["uncertainty_message"] = str(uncertainty)
        if uncertainty.scenarios:
            res.fields["candidate_scenarios"] = uncertainty.scenarios
    except guards.GuardViolation as violation:
        res.note_guard(violation.guard_id)
        res.payable = None
        res.status = violation.violation_status
        res.reason = str(violation)
        res.fields["guard_violation"] = violation.guard_id
        res.label(violation.guard_id)
    except PlanError as error:
        res.payable = None
        res.payable_scenarios = []
        res.status = "EXECUTION_PLAN_INVALID"
        res.reason = str(error)
        res.fields["execution_plan_error"] = str(error)
        res.label("EXECUTION_PLAN_INVALID")
    except ClassificationEvidenceRequired as error:
        res.payable = None
        res.status = "CLASSIFICATION_EVIDENCE_REQUIRED"
        res.reason = str(error)
        classification = res.fields.get("classification")
        if isinstance(classification, dict):
            classification["outcome"] = "INSUFFICIENT_EVIDENCE"
            classification["reason"] = str(error)
        res.label("CLASSIFICATION_EVIDENCE_REQUIRED")
    except operators.OperatorError as error:
        res.payable = None
        res.status = "INPUT_ERROR"
        res.reason = str(error)
    except CaseInputError as error:
        res.payable = None
        res.status = "INPUT_ERROR"
        res.reason = str(error)

    _reconcile_authorization_uncertainties(res)

    try:
        if res.branch in BODY_BRANCHES:
            res.require_guard("G_UNCERTAINTY_MUST_SURFACE")
        guards.check_uncertainty_propagation(res)
        res.note_guard("G_UNCERTAINTY_MUST_SURFACE")
    except guards.GuardViolation as violation:
        res.note_guard(violation.guard_id)
        res.payable = None
        res.status = violation.violation_status
        res.reason = str(violation)
        res.fields["guard_violation"] = violation.guard_id
        res.label(violation.guard_id)

    _enforce_guard_plan(res)
    _finalize(res, kb, case)
    _apply_authorization_confidence_cap(res)
    return res
