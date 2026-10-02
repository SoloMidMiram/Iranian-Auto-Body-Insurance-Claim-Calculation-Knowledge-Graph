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

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Callable

from . import guards, money, operators
from .case import DOMAIN_BY_BRANCH, Case, CaseInputError
from .classify import classify
from .knowledge import Knowledge

UNRESOLVED_ORDER = "UNRESOLVED"


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
    provenance: list[dict[str, Any]] = field(default_factory=list)

    def label(self, *names: str) -> None:
        for name in names:
            if name:
                self.labels.add(name)

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
            "provenance": self.provenance,
        }


def _out(value: Any) -> Any:
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else format(value, "f")
    if isinstance(value, dict):
        return {key: _out(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_out(item) for item in value]
    return value


# --------------------------------------------------------------------- helpers


def _rescue(case: Case, res: CalcResult, cap_base: Decimal) -> Decimal:
    actual = case.rescue_actual or Decimal(0)
    cap = operators.allowable_rescue_transport(actual, cap_base)
    res.fields["rescue_cap"] = operators.RESCUE_CAP_RATIO * cap_base if cap_base > 0 else Decimal(0)
    res.fields["allowable_rescue_transport"] = cap
    res.fields["rescue_claimed"] = actual
    if actual > 0:
        res.note_rule("REG53_RESCUE_TRANSPORT_CAP")
        if cap < actual:
            res.label("RESCUE_CAPPED")
    return cap


def _ratio(case: Case, res: CalcResult) -> Decimal:
    """Apply the underinsurance ratio, or record that it was not assessable."""
    market = case.market_value
    insured = case.insured_sum
    if market is None and insured is None:
        res.fields["article10_ratio"] = Decimal(1)
        res.label("UNDERINSURANCE_NOT_ASSESSED")
        return Decimal(1)
    ratio = operators.underinsurance_ratio(insured, market)
    res.fields["article10_ratio"] = ratio
    res.note_rule("REG53_ART20_NOTE2_UNDERINSURANCE_RATIO")
    if ratio < 1:
        res.label("UNDERINSURANCE_APPLIED")
    return ratio


def _resolve_franchise(case: Case, res: CalcResult, base: Decimal) -> Decimal:
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
        res.fields["franchise"] = Decimal(0)
        res.fields["franchise_source"] = "NOT_SPECIFIED"
        res.label("FRANCHISE_NOT_SPECIFIED")
        return Decimal(0)

    mode = str(spec.get("mode", "ABSOLUTE")).upper()
    guards.check_franchise_source(case, mode, source)

    def _dec(value: Any) -> Decimal | None:
        return None if value is None else money.D(value)

    amount = operators.franchise_amount(
        mode,
        base=base,
        rate=_dec(spec.get("rate")),
        absolute=_dec(spec.get("absolute_irr", spec.get("absolute"))),
        minimum=_dec(spec.get("minimum_irr", spec.get("minimum"))),
    )
    res.fields["franchise"] = amount
    res.fields["franchise_mode"] = mode
    res.fields["franchise_source"] = source or "UNKNOWN"
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

    theft_types = predicate.get("theft_type_in")
    if theft_types and case.theft_type in theft_types:
        return True

    field = predicate.get("field")
    if field:
        value = case.field_value(field)
        if value is not None and value == predicate.get("equals"):
            return True

    keywords = predicate.get("cause_keywords")
    if keywords:
        haystack = " ".join(filter(None, [case.cause or "", case.peril or ""])).upper()
        for keyword in keywords:
            if keyword.upper() in haystack:
                return True

    return False


def evaluate_coverage_gate(case: Case, kb: Knowledge, res: CalcResult) -> bool:
    """Coverage, causation and exclusion gate. Returns True when it settles the claim."""
    # Article 6 non-compensable circumstances defeat cover outright.
    for exclusion in kb.exclusions.values():
        if exclusion.get("type") != "NON_COMPENSABLE":
            continue
        if _exclusion_matches(case, exclusion):
            outcome = exclusion["uninsured_outcome"]
            res.payable = money.D(outcome.get("payable", 0))
            res.reason = outcome.get("reason", "NON_COMPENSABLE")
            res.fields["exclusion_applied"] = exclusion["node_id"]
            res.fields["exclusion_state"] = "NON_COMPENSABLE"
            res.note_rule("REG53_ART6_NON_COMPENSABLE")
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
            outcome = exclusion.get("insured_outcome") or {}
            res.payable = None
            res.status = outcome.get("status", "ENDORSEMENT_TERMS_REQUIRED")
            res.label("ENDORSEMENT_TERMS_REQUIRED")
            res.fields["endorsement_terms_needed"] = exclusion.get("endorsement_terms_needed", [])
            res.block("U02_FRANCHISE_BASE_SCHEDULES")
            return True
        outcome = exclusion["uninsured_outcome"]
        res.payable = money.D(outcome.get("payable", 0))
        res.reason = outcome.get("reason", "EXCLUDED_WITHOUT_ENDORSEMENT")
        res.label("EXCLUDED_WITHOUT_ENDORSEMENT")
        return True

    if case.late_notice_issue:
        res.label("LATE_NOTICE_REVIEW")
        res.note_rule("REG53_NOTICE_AND_DUTIES")
    if case.subrogation_impaired:
        res.label("SUBROGATION_IMPAIRMENT_REVIEW")
        res.note_rule("REG53_ART14_SUBROGATION")
    return False


# ------------------------------------------------------------- partial damage


def calculate_partial_damage(case: Case, kb: Knowledge, res: CalcResult) -> None:
    res.label("PARTIAL_DAMAGE")
    res.note_rule("REG53_ART19B_PARTIAL_LOSS_BASE")

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
        depreciation = Decimal(0)
        res.fields["depreciation_source"] = "NONE"

    after_depreciation = eligible - depreciation
    res.fields["assessed_gross"] = assessed
    res.fields["gross_eligible"] = eligible
    res.fields["eligible_before_other_terms"] = eligible
    res.fields["depreciation"] = depreciation
    res.fields["after_depreciation"] = after_depreciation

    cap_kind = str(case.config.get("rescue_cap_base", "ASSESSED_GROSS")).upper()
    if cap_kind == "ELIGIBLE_GROSS":
        cap_base = eligible
    elif cap_kind == "SETTLEMENT_BASE":
        cap_base = after_depreciation
    else:
        cap_base = assessed
    res.fields["rescue_cap_base_kind"] = cap_kind
    if cap_base != eligible:
        res.label("RESCUE_DENOMINATOR_CONFIGURED")
    rescue = _rescue(case, res, cap_base)

    franchise = _resolve_franchise(case, res, after_depreciation)
    ratio = _ratio(case, res)
    order = str(case.config.get("article10_partial_order", UNRESOLVED_ORDER)).upper()

    if ratio == 1:
        res.fields["order_used"] = "RATIO_NOT_APPLICABLE"
        res.payable = max(Decimal(0), after_depreciation - franchise + rescue)
        return

    if order == "AFTER_DEPRECIATION_BEFORE_FRANCHISE":
        res.fields["order_used"] = order
        res.payable = max(Decimal(0), after_depreciation * ratio - franchise + rescue)
        return

    if order == "AFTER_DEPRECIATION_AND_FRANCHISE":
        res.fields["order_used"] = order
        res.payable = max(Decimal(0), (after_depreciation - franchise) * ratio + rescue)
        return

    ratio_first = max(Decimal(0), after_depreciation * ratio - franchise + rescue)
    franchise_first = max(Decimal(0), (after_depreciation - franchise) * ratio + rescue)
    res.fields["scenario_ratio_then_franchise"] = ratio_first
    res.fields["scenario_franchise_then_ratio"] = franchise_first
    res.payable_scenarios = [ratio_first, franchise_first]
    res.payable = None
    res.status = "ORDER_UNRESOLVED"
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
    res.note_rule("REG53_ART19_TOTAL_LOSS_VALUATION")

    if insured < market:
        res.fields["underinsurance_ratio_equivalent"] = insured / market
        res.fields["guard_ratio_twice"] = "PROHIBITED"
        res.note_rule("REG53_ART19_TOTAL_LOSS_NO_DOUBLE_UNDERINSURANCE")
        res.label("DO_NOT_APPLY_RATIO_TWICE")

    disposition = case.salvage_disposition
    if disposition == "UNRESOLVED":
        raise operators.UncertaintyRequired(
            "U12_SALVAGE_DISPOSITION",
            "salvage disposition is unresolved, so the settlement base cannot be fixed",
            status="SALVAGE_DISPOSITION_UNRESOLVED",
        )

    if disposition == "INSURER_TAKES_TITLE":
        after_salvage = base
        res.fields["salvage_deduction"] = Decimal(0)
        res.fields["salvage_disposition"] = disposition
        res.note_rule("REG53_ART19_INSURER_TAKES_TITLE")
        res.label("DO_NOT_DEDUCT_SALVAGE_AND_TRANSFER_IT")
    else:
        salvage = case.salvage or Decimal(0)
        after_salvage = base - salvage
        res.fields["salvage_deduction"] = salvage
        res.fields["salvage_disposition"] = disposition
        if salvage > 0:
            res.note_rule("CIC_CIRC_1400_401_146850_SALVAGE_BEFORE_FRANCHISE")
            res.label("SALVAGE_DEDUCTED_BEFORE_FRANCHISE")
    res.fields["base_after_salvage"] = after_salvage

    repair = case.repair_total
    rescue = _rescue(case, res, repair if repair is not None else base)
    franchise = _resolve_franchise(case, res, after_salvage)

    result = after_salvage - franchise + rescue
    capped = min(result, insured)
    if capped != result:
        res.label("INSURED_SUM_CEILING_APPLIED")
    res.payable = max(Decimal(0), capped)


def calculate_total_loss(case: Case, kb: Knowledge, res: CalcResult) -> None:
    res.label("TOTAL_LOSS")
    market = case.market_value
    repair = case.repair_total
    is_total, combined, threshold = operators.is_total_loss(
        repair, case.rescue_for_threshold, market
    )
    if combined is not None:
        res.fields["combined_for_threshold"] = combined
        res.fields["threshold_value"] = threshold
        res.fields["threshold_ratio"] = combined / market if market else None
        res.fields["is_total"] = is_total
        res.note_rule("REG53_ART19_TOTAL_LOSS_THRESHOLD")

    if is_total is False:
        res.payable = None
        if threshold is not None and combined == threshold:
            res.reason = "EXACTLY_75_PERCENT_IS_NOT_MORE_THAN_75_PERCENT"
            res.label("THRESHOLD_EQUALITY_NOT_TOTAL_LOSS")
        else:
            res.reason = "NOT_TOTAL_LOSS"
            res.label("NOT_TOTAL_LOSS")
        return

    if res.variant == "THRESHOLD_TEST":
        res.fields["is_total"] = is_total
        res.payable = None
        return

    _settle_total_loss(case, kb, res)


# --------------------------------------------------------------------- glass


def calculate_glass(case: Case, kb: Knowledge, res: CalcResult) -> None:
    res.label("GLASS_ONLY")
    guards.check_universal_glass_franchise(case)

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

    rescue = _rescue(case, res, gross)
    franchise = _resolve_franchise(case, res, gross)
    ratio = _ratio(case, res)
    order = str(case.config.get("article10_partial_order", UNRESOLVED_ORDER)).upper()
    contractually_resolved = bool(case.config.get("glass_article10_order_resolved_by_endorsement"))

    if ratio == 1:
        res.fields["order_used"] = "RATIO_NOT_APPLICABLE"
        res.payable = max(Decimal(0), gross - franchise + rescue)
        return

    if contractually_resolved and order == "AFTER_DEPRECIATION_BEFORE_FRANCHISE":
        res.fields["order_used"] = order
        res.payable = max(Decimal(0), gross * ratio - franchise + rescue)
        return

    if contractually_resolved and order == "AFTER_DEPRECIATION_AND_FRANCHISE":
        res.fields["order_used"] = order
        res.payable = max(Decimal(0), (gross - franchise) * ratio + rescue)
        return

    ratio_first = max(Decimal(0), gross * ratio - franchise + rescue)
    franchise_first = max(Decimal(0), (gross - franchise) * ratio + rescue)
    res.fields["scenario_ratio_then_franchise"] = ratio_first
    res.fields["scenario_franchise_then_ratio"] = franchise_first
    res.payable_scenarios = [ratio_first, franchise_first]
    res.payable = None
    res.status = "ENDORSEMENT_AND_ORDER_REQUIRED"
    res.block("U03_GLASS_ONLY_ENDORSEMENT_WORDING", "U11_GLASS_ARTICLE10_EXEMPTION")
    res.label("GLASS_UNDERINSURANCE_UNRESOLVED")


# --------------------------------------------------------------------- theft


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
    guards.check_article8_method(case)

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

    actual = case.actual_damage or corresponding
    insurer_payable = min(corresponding, limit)
    excess = max(Decimal(0), actual - corresponding)

    res.fields["actual_damage"] = actual
    res.fields["corresponding_damage"] = corresponding
    res.fields["insurer_payable"] = insurer_payable
    res.fields["tp_insurer_payable"] = insurer_payable
    res.fields["remaining_inside_article8_cap"] = max(Decimal(0), corresponding - insurer_payable)
    res.fields["non_corresponding_excess"] = excess
    res.fields["own_body_excess_candidate"] = excess
    res.fields["own_body_non_corresponding_excess_candidate"] = excess
    res.note_rule(
        "HIC_ARTICLE8_CORRESPONDING_DAMAGE", "TPL_LAW_1395_ART8_NON_CONVENTIONAL_LIMIT"
    )
    if insurer_payable < corresponding:
        res.label("DUAL_CAP_APPLIED")

    if res.variant == "DUAL_COVERAGE":
        res.fields["third_party"] = insurer_payable
        res.note_rule("CIC_CIRC_1404_06_10_ARTICLE8_EXCESS_OWN_BODY")
        if case.has_body_policy:
            if case.body_franchise_for_excess_disclosed:
                res.fields["body_candidate_before_disclosed_terms"] = excess
                res.label("APPLY_VALID_DISCLOSED_POLICY_TERM")
            else:
                res.fields["body_candidate_before_other_body_terms"] = excess
                res.fields["regulatory_mandatory_franchise_on_this_excess"] = money.D(0)
                res.note_rule("CIC_CIRC_1404_06_10_NO_MANDATORY_FRANCHISE_ON_ART8_EXCESS")
        res.payable = insurer_payable
        return

    if case.has_body_policy is False:
        res.fields["tp_or_at_fault_statutory_cap"] = corresponding
        res.fields["non_corresponding_residual"] = excess
        res.label("AT_FAULT_CAP_APPLIED")
        res.note_rule("TPL_LAW_1395_ART8_AT_FAULT_CAP")
        res.payable = corresponding
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


# --------------------------------------------------------------------- driver


def _finalize(res: CalcResult, kb: Knowledge, case: Case) -> None:
    confidences: list[float] = []
    provenance: list[dict[str, Any]] = []
    for rule_id in res.rule_trace:
        rule = kb.rule(rule_id)
        if rule is not None:
            confidences.append(float(rule.get("confidence", 0.0)))
            provenance.append(kb.provenance(rule_id))
    for uncertainty_id in res.blocking_uncertainties:
        uncertainty = kb.uncertainty(uncertainty_id)
        if uncertainty is not None and uncertainty.get("confidence_of_single_interpretation") is not None:
            confidences.append(float(uncertainty["confidence_of_single_interpretation"]))
    res.formula_confidence = min(confidences) if confidences else None
    res.provenance = provenance
    if res.blocking_uncertainties:
        res.label("BLOCKING_UNCERTAINTY_SURFACED")
    if res.payable is not None:
        res.payable = money.round_irr(res.payable)
    res.payable_scenarios = [money.round_irr(value) for value in res.payable_scenarios]


def compute(case: Case | dict[str, Any], kb: Knowledge | None = None) -> CalcResult:
    from .schema_input import validated_case

    case = validated_case(case)
    kb = kb or Knowledge.load()

    res = CalcResult(
        branch=case.branch,
        variant=case.variant,
        domain=case.domain,
        claim_id=case.claim_id,
        unit=case.unit,
    )

    if res.branch is None:
        guessed = classify(case, kb)
        res.branch = guessed["branch"]
        res.variant = guessed["variant"]
        res.domain = res.domain or DOMAIN_BY_BRANCH.get(guessed["branch"])
        res.fields["classification"] = {
            "branch": guessed["branch"],
            "variant": guessed["variant"],
            "confidence": guessed["confidence"],
            "basis": guessed["basis"],
        }

    try:
        if not evaluate_coverage_gate(case, kb, res):
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
        res.payable = None
        res.status = violation.violation_status
        res.reason = str(violation)
        res.fields["guard_violation"] = violation.guard_id
        res.label(violation.guard_id)
    except operators.OperatorError as error:
        res.payable = None
        res.status = "INPUT_ERROR"
        res.reason = str(error)
    except CaseInputError as error:
        res.payable = None
        res.status = "INPUT_ERROR"
        res.reason = str(error)

    try:
        guards.check_uncertainty_propagation(res)
    except guards.GuardViolation as violation:
        res.payable = None
        res.status = violation.violation_status
        res.reason = str(violation)
        res.fields["guard_violation"] = violation.guard_id
        res.label(violation.guard_id)

    _finalize(res, kb, case)
    return res
