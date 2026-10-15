"""Case review: the investigation layer that runs *before* the calculation engine.

    answers -> questions still open -> parameter slots -> branch -> ladder tier
            -> decision (COMPUTE / SCENARIO_SET / REFUSE / INSUFFICIENT) -> engine

Three rules give this module its shape:

1. **The questionnaire cannot calculate.** An answer may only bind a
   ``ParameterSlot`` declared in knowledge/parameter_slots.json, name evidence, or
   route the case. Rates, orders and formulas live in the graph; a form that could
   set one would be a way to fabricate authority.
2. **Absence is recorded, never invented.** An unanswered blocking question, or a
   slot whose only source is a document nobody has read, produces a named gap and
   the decision stops at INSUFFICIENT. UNKNOWN is a real answer and is treated as
   one.
3. **Money answers are non-negative integer IRR**, exactly like the worked
   examples in ``cases/``. Display-unit conversion is a presentation concern.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from . import money
from .admission import (
    AUTHORIZED_DECISIONS,
    _issue_review_authorization,
    AuthorizationNotGranted,
    CalculationAuthorization,
    utc_now,
)
from .case import PART_CATEGORIES
from .classify import classify
from .dates import CalendarDateError, parse_claim_date
from .engine import CalcResult, compute, reconcile_classification
from .knowledge import Knowledge
from .schema_input import load_json_document, validate_review, validated_case

# Answers that mean "this file does not say". They bind nothing.
UNANSWERED_TOKENS = {"", None, "UNKNOWN", "NOT_STATED", "NOT_REVIEWED", "NOT_APPLICABLE_TO_BODY"}

# Regulation 53 treats an expired licence as *not* the same thing as a void one, so
# the non-compensable exclusion may only fire on the states that are actually void
# or absent. Anything unproven is left unanswered rather than defaulted to True.
LICENCE_DEFEATS_COVER = {"VOID_OR_SUSPENDED", "WRONG_CLASS", "UNLICENSED"}
LICENCE_HOLDS_COVER = {"VALID_AND_APPROPRIATE", "EXPIRED", "NOT_DRIVING"}

DECISION_COMPUTE = "COMPUTE"
DECISION_SCENARIO = "SCENARIO_SET"
DECISION_REFUSE = "REFUSE"
DECISION_INSUFFICIENT = "INSUFFICIENT_INFORMATION"

# Missing documents with these tokens stop a handoff. ROUTE_TO_REVIEW is reported
# only, and REDUCE_CONFIDENCE still calculates under the evidence node's cap.
STOPPING_IF_ABSENT = frozenset({"REFUSE_INTAKE", "BLOCK_PARAMETER", "ESCALATE_INSURER"})

STATUS_RESOLVED = "RESOLVED"
STATUS_MISSING = "MISSING"
STATUS_UNANSWERED = "UNANSWERED"
STATUS_DERIVED = "DERIVED"
STATUS_NOT_APPLICABLE = "NOT_APPLICABLE"
STATUS_NOT_TRIGGERED = "NOT_TRIGGERED"


class ReviewInputError(ValueError):
    pass


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _is_number(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    return isinstance(value, (int, float, Decimal, str)) and _parses(value)


def _parses(value: Any) -> bool:
    try:
        money.D(value)
    except (InvalidOperation, TypeError, ValueError):
        return False
    return True


@dataclass
class SlotBinding:
    """One parameter slot as this file currently leaves it."""

    slot_id: str
    name: str
    status: str
    value: Any = None
    unit: str = ""
    authority: str = ""
    supplied_via: list[str] = field(default_factory=list)
    supplied_by: list[str] = field(default_factory=list)
    missing_behavior: str = ""
    blocking_uncertainty: str | None = None
    guardrail: str | None = None
    case_field: str = ""
    select: str = ""
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "slot": self.slot_id,
            "status": self.status,
            "value": self.value,
            "unit": self.unit,
            "authority": self.authority,
            "supplied_via": self.supplied_via,
            "supplied_by": self.supplied_by,
            "missing_behavior": self.missing_behavior,
            "blocking_uncertainty": self.blocking_uncertainty,
            "guardrail": self.guardrail,
            "case_field": self.case_field,
            "note": self.note,
        }


class Review:
    """A claim file under investigation: what is answered, what is still open, and
    whether an amount may be issued yet."""

    authorization_kind = "CLAIM_FILE"

    def __init__(self, payload: dict[str, Any], kb: Knowledge | None = None) -> None:
        self.kb = kb or Knowledge.load()
        validate_review(payload, self.kb)
        self.claim_id = str(payload.get("claim_id") or payload.get("id") or "unnamed-review")
        self.unit = payload.get("unit") or "IRR"
        self.payload = payload
        self.answers: dict[str, Any] = dict(payload.get("answers") or {})
        self.slots: dict[str, SlotBinding] = {}
        self._bound: dict[str, Any] = {}
        self.bind()

    @classmethod
    def from_file(cls, path: Path | str, kb: Knowledge | None = None) -> "Review":
        return cls(load_json_document(path), kb)

    # ------------------------------------------------------------------ answers

    def answer(self, question_id: str) -> Any:
        return self.answers.get(question_id)

    def is_answered(self, question_id: str) -> bool:
        if question_id not in self.answers:
            return False
        value = self.answers[question_id]
        if isinstance(value, str) and value.upper() in UNANSWERED_TOKENS:
            return False
        return value not in (None, "", [], {})

    # --------------------------------------------------------------- predicates

    def holds(self, predicate: Any) -> bool:
        """Evaluate the shared gate/when language. Unknown shapes are False, never a guess."""
        if not isinstance(predicate, dict):
            return True
        if "always" in predicate:
            return bool(predicate["always"])
        if "all" in predicate:
            return all(self.holds(child) for child in predicate["all"])
        if "any" in predicate:
            return any(self.holds(child) for child in predicate["any"])
        if "not" in predicate:
            return not self.holds(predicate["not"])
        if "answered" in predicate:
            return all(self.is_answered(item) for item in _as_list(predicate["answered"]))
        if "unanswered" in predicate:
            return any(not self.is_answered(item) for item in _as_list(predicate["unanswered"]))
        if "stage_open" in predicate:
            return all(
                any(
                    q.get("stage") == stage and not self.is_answered(q["node_id"])
                    for q in self.kb.questions.values()
                )
                for stage in _as_list(predicate["stage_open"])
            )
        if "answer_is" in predicate:
            spec = predicate["answer_is"]
            if not isinstance(spec, list) or not spec:
                return False
            question_id = spec[0]
            wanted = {str(item) for item in _as_list(spec[1])} if len(spec) > 1 else set()
            value = self.answer(question_id)
            if value is None:
                return False
            got = {str(item) for item in _as_list(value)}
            return bool(got & wanted) if wanted else bool(got)
        if "slot_present" in predicate:
            slot_id = predicate["slot_present"]
            value = self._bound.get(slot_id)
            if value in (None, "", [], {}):
                return False
            category = predicate.get("category")
            if category is not None:
                tokens = {
                    item.get("category") if isinstance(item, dict) else str(item)
                    for item in _as_list(value)
                }
                return str(category) in {str(token) for token in tokens}
            expected = predicate.get("value")
            if expected is not None:
                return any(str(item) == str(expected) for item in _as_list(value))
            return True
        if "slot_live" in predicate:
            return self.uncertainty_is_live(str(predicate["slot_live"]))
        if "branch_is" in predicate:
            branch = self.classification().get("branch")
            wanted = {self.kb.canonical_branch(str(item)) for item in _as_list(predicate["branch_is"])}
            return branch in wanted
        return False

    # ------------------------------------------------------------------ binding

    def _apply_binding(self, question: dict, binding: dict) -> None:
        slot_id = binding.get("slot")
        slot = self.kb.slot(slot_id or "")
        if slot is None:
            return
        when_answer = binding.get("when_answer")
        value = self.answer(question["node_id"])
        if when_answer is not None:
            wanted = {str(item) for item in _as_list(when_answer)}
            got = {str(item) for item in _as_list(value)}
            if not (got & wanted):
                return
        if "value" in binding:
            value = binding["value"]
        if derive := binding.get("derive"):
            self._bound.setdefault(slot_id, None)
            self._derive(slot_id, str(derive))
            return

        fmt = question.get("answer_format")
        if slot.get("unit") in ("money", "ratio") and not _is_number(value):
            return  # a qualitative answer cannot be a measurement
        if slot.get("unit") == "money" and fmt == "money":
            value = money.D(value)
        if slot.get("unit") == "integer" and fmt != "integer":
            return

        current = self._bound.get(slot_id)
        if slot.get("unit") == "object":
            self._bound[slot_id] = _merge_object(current, value, binding.get("field"))
            return
        if slot.get("unit") in ("list", "enum") and isinstance(value, list):
            self._bound[slot_id] = value
        else:
            self._bound[slot_id] = value

    def bind(self) -> None:
        """Bind in order, then resolve gates depending on later-recorded slots."""
        for _ in range(2):
            self._classification_cache = None
            for question in self.kb.ordered_questions():
                if not self.is_answered(question["node_id"]):
                    continue
                when = question.get("when")
                if when and not self.holds(when):
                    continue
                for binding in question.get("sets") or []:
                    if not isinstance(binding, dict):
                        continue
                    self._apply_binding(question, binding)
            self._derive_dependent_slots()
        self._classification_cache = None

    def _derive_dependent_slots(self) -> None:
        """Recompute the slots that are functions of other slots, never of opinions.

        The underinsurance ratio is the only one the calculation actually needs from
        the review layer, and it is the one value an adjuster most often mis-states,
        so it is derived here from the two evidenced figures rather than asked.
        """
        market = self._bound.get("PS_MARKET_VALUE")
        insured = self._bound.get("PS_INSURED_SUM")
        if market and insured:
            self._bound["PS_UNDERINSURANCE_RATIO"] = min(
                Decimal(1), money.D(insured) / money.D(market)
            )
        # An itemised assessment *is* the repair-and-replacement figure the total-loss
        # test needs; deriving it keeps the 75% test from silently skipping.
        if self._bound.get("PS_REPAIR_TOTAL") is None:
            records = [item for item in _as_list(self._bound.get("PS_PART_CATEGORY")) if isinstance(item, dict)]
            if records:
                total = sum(
                    (
                        money.D(item.get("assessed_loss", item.get("assessed_loss_irr", 0)) or 0)
                        for item in records
                    ),
                    Decimal(0),
                )
                total += money.D(self._bound.get("PS_LABOR") or 0)
                self._bound["PS_REPAIR_TOTAL"] = total
                if self._bound.get("PS_GROSS_DAMAGE") is None:
                    self._bound["PS_GROSS_DAMAGE"] = total

    def _derive(self, slot_id: str, derivation: str) -> None:
        if derivation == "iranian_year_of_event":
            raw = self.answer("Q-S0-02")
            if raw not in (None, ""):
                self._bound[slot_id] = parse_claim_date(raw).iranian_year
        elif derivation == "underinsurance_ratio":
            market = self._bound.get("PS_MARKET_VALUE")
            insured = self._bound.get("PS_INSURED_SUM")
            if market and insured:
                self._bound[slot_id] = min(Decimal(1), money.D(insured) / money.D(market))

    # ------------------------------------------------------------------- slots

    def slot_status(self, slot_id: str) -> SlotBinding:
        if slot_id in self.slots:
            return self.slots[slot_id]
        node = self.kb.slot(slot_id) or {}
        binding = SlotBinding(
            slot_id=slot_id,
            name=str(node.get("name") or slot_id),
            status=STATUS_MISSING,
            unit=str(node.get("unit") or ""),
            authority=str(node.get("authority") or ""),
            supplied_via=list(node.get("supplied_via") or []),
            supplied_by=list(node.get("supplied_by") or []),
            missing_behavior=str(node.get("missing_behavior") or "REFUSE"),
            blocking_uncertainty=node.get("blocking_uncertainty"),
            guardrail=node.get("guardrail"),
            case_field=str(node.get("case_field") or ""),
            select=str(node.get("select") or ""),
        )
        if slot_id in self._bound and self._bound[slot_id] not in (None, "", [], {}):
            binding.value = self._bound[slot_id]
            binding.status = STATUS_DERIVED if binding.authority == "DERIVED" else STATUS_RESOLVED
        else:
            fillers = [q["node_id"] for q in self.kb.questions_filling_slot(slot_id)]
            answered = [q for q in fillers if self.is_answered(q)]
            applicable = [
                q
                for q in fillers
                if self.is_answered(q)
                or self.holds((self.kb.question(q) or {}).get("when"))
            ]
            if answered:
                binding.status = STATUS_NOT_TRIGGERED
                binding.note = "answered; the slot is only read when the answer triggers it"
            elif fillers and not applicable:
                binding.status = STATUS_NOT_APPLICABLE
                binding.note = "the question that would supply it is not asked for this file"
            elif fillers:
                binding.status = STATUS_UNANSWERED
                binding.supplied_by = fillers
                binding.note = "no answer yet binds this slot"
        self.slots[slot_id] = binding
        return binding

    def slots_for(self, branch: str) -> list[SlotBinding]:
        return [self.slot_status(node["node_id"]) for node in self.kb.slots_for_branch(branch)]

    # ------------------------------------------------------------- liveness of U

    def uncertainty_is_live(self, uncertainty_id: str) -> bool:
        """Whether an unresolved variable actually bites *this* file.

        The graph marks several uncertainties blocking in the abstract; only the
        case facts decide whether one is live. Each test below mirrors a
        ``live_only_when`` clause in knowledge/uncertainties.json.
        """
        node = self.kb.uncertainty(uncertainty_id)
        if node is None or not node.get("blocking"):
            return False
        branch = self.classification().get("branch") or ""

        def slot(slot_id: str) -> Any:
            return self._bound.get(slot_id)

        if uncertainty_id == "U01_ARTICLE10_PARTIAL_ORDER":
            ratio = slot("PS_UNDERINSURANCE_RATIO")
            return bool(ratio) and branch in ("PARTIAL_DAMAGE", "GLASS_ONLY") and float(ratio) < 1.0
        if uncertainty_id == "U04_BATTERY_TIRE_CAP_VS_DEPRECIATION":
            parts = [item for item in _as_list(slot("PS_PART_CATEGORY")) if isinstance(item, dict)]
            special = any(
                str(item.get("category")) in ("BATTERY", "TIRE")
                and bool(item.get("requires_replacement", True))
                for item in parts
            )
            year = slot("PS_PRODUCTION_YEAR")
            claim_year = slot("PS_CLAIM_YEAR")
            index = (int(claim_year) - int(year) + 1) if year is not None and claim_year is not None else 0
            return special and index >= 5
        if uncertainty_id == "U05_RESCUE_DENOMINATOR":
            return _is_number(slot("PS_RESCUE_ACTUAL")) and money.D(slot("PS_RESCUE_ACTUAL")) > 0
        if uncertainty_id == "U12_SALVAGE_DISPOSITION":
            return str(slot("PS_SALVAGE_DISPOSITION") or "") == "UNRESOLVED"
        if uncertainty_id == "U13_THEFT_CLOCK_ANCHOR":
            return (
                str(slot("PS_THEFT_TYPE") or "") == "WHOLE_VEHICLE"
                and self._theft_clock() is None
            )
        if uncertainty_id == "U14_GLASS_INSURED_AT_VALUE_CONDITION":
            return branch == "GLASS_ONLY" and str(slot("PS_GLASS_VALUATION_CONDITION") or "") == (
                "REQUIRES_INSURED_AT_MARKET_VALUE"
            )
        if uncertainty_id == "U15_RISK_INTENSIFICATION_PREMIUM_RATIO":
            return bool(slot("PS_RISK_INTENSIFICATION"))
        if uncertainty_id == "U02_FRANCHISE_BASE_SCHEDULES":
            return branch in ("PARTIAL_DAMAGE", "TOTAL_LOSS", "GLASS_ONLY", "THEFT") and not self._franchise_complete()
        if uncertainty_id in ("U03_GLASS_ONLY_ENDORSEMENT_WORDING", "U11_GLASS_ARTICLE10_EXEMPTION"):
            return branch == "GLASS_ONLY"
        if uncertainty_id == "U06_ARTICLE8_COMPONENT_CATALOGUE":
            return branch == "ARTICLE_8_NON_CONVENTIONAL" and slot("PS_MARKET_VALUE") is None
        return branch in (node.get("affects_branches") or [])

    def _franchise_complete(self) -> bool:
        franchise = self._bound.get("PS_FRANCHISE")
        if not isinstance(franchise, dict):
            return False
        mode = str(franchise.get("mode") or "").upper()
        if mode in ("", "NOT_STATED"):
            return False
        if franchise.get("source") not in ("POLICY", "ENDORSEMENT", "INSURER_MANUAL"):
            return False
        if mode.startswith("PERCENT"):
            if franchise.get("rate") is None or franchise.get("calculation_base") is None:
                return False
            if mode == "PERCENT_WITH_MINIMUM" and franchise.get(
                "minimum_irr", franchise.get("minimum")
            ) is None:
                return False
        elif franchise.get("absolute_irr", franchise.get("absolute")) is None:
            return False

        amount = franchise.get("absolute_irr", franchise.get("absolute"))
        rate = franchise.get("rate")
        if amount == 0 or rate == 0:
            return bool(
                franchise.get("source") in ("POLICY", "ENDORSEMENT", "INSURER_MANUAL")
                and franchise.get("source_reference")
                and franchise.get("source_version")
            )
        return True

    def _theft_clock(self) -> dict[str, Any] | None:
        """Return the complete, source-bound whole-theft clock or no clock.

        A partial group must never reach the case schema: the review remains
        blocked by its unanswered questions and U13 until all five fields exist
        and the selected start event agrees with its canonical case date.
        """
        fields = {
            "start_event": self._bound.get("PS_THEFT_CLOCK_START_EVENT"),
            "start_date": self._bound.get("PS_THEFT_CLOCK_START_DATE"),
            "as_of_date": self._bound.get("PS_THEFT_CLOCK_AS_OF_DATE"),
            "calendar": self._bound.get("PS_THEFT_CLOCK_CALENDAR"),
            "source": self._bound.get("PS_THEFT_CLOCK_SOURCE"),
        }
        if any(value in (None, "", [], {}) for value in fields.values()):
            return None
        start_event = str(fields["start_event"])
        event_date_slot = {
            "THEFT_OCCURRENCE": "PS_EVENT_DATE",
            "AWARENESS": "PS_AWARENESS_DATE",
            "DECLARATION": "PS_DECLARATION_DATE",
        }.get(start_event)
        if event_date_slot is None:
            return None
        canonical_date = self._bound.get(event_date_slot)
        if canonical_date in (None, ""):
            return None
        try:
            start_key = parse_claim_date(
                fields["start_date"], calendar=str(fields["calendar"])
            ).chronology_key
            event_key = parse_claim_date(canonical_date).chronology_key
        except CalendarDateError:
            return None
        if start_key != event_key:
            return None
        return {key: str(value) for key, value in fields.items()}

    # ------------------------------------------------------------ case emission

    def case_payload(self) -> dict[str, Any]:
        """The schema-shaped case a completed review hands to the engine."""
        slot_value = lambda key: self._bound.get(key)  # noqa: E731

        def irr(value: Any) -> Any:
            if isinstance(value, Decimal) and value == value.to_integral_value():
                return int(value)
            return value

        def part_records() -> list[dict[str, Any]]:
            records = []
            for item in _as_list(slot_value("PS_PART_CATEGORY")):
                if isinstance(item, dict):
                    category = str(item.get("category") or "OTHER_REPLACEMENT_PART")
                    record: dict[str, Any] = {
                        "category": category,
                        "assessed_loss_irr": irr(item.get("assessed_loss", item.get("assessed_loss_irr", 0))),
                        "requires_replacement": bool(
                            item.get("requires_replacement", category != "REPAIR_ONLY")
                        ),
                    }
                    if isinstance(item.get("name"), str) and item["name"]:
                        record["name"] = item["name"]
                    new_price = item.get("new_price", item.get("new_price_irr"))
                    if new_price is not None:
                        record["new_price_irr"] = irr(new_price)
                    records.append(record)
                elif str(item) in PART_CATEGORIES:
                    records.append({"category": str(item), "assessed_loss_irr": 0})
            return records

        parts = part_records()
        new_price = slot_value("PS_PART_NEW_PRICE")
        if new_price is not None:
            for record in parts:
                if record["category"] in ("BATTERY", "TIRE") and record.get("new_price_irr") in (None, 0):
                    record["new_price_irr"] = irr(new_price)

        franchise = slot_value("PS_FRANCHISE")
        multiple_insurance = slot_value("PS_MULTIPLE_POLICIES")
        endorsements = [
            str(item).upper()
            for item in _as_list(slot_value("PS_ENDORSEMENTS"))
            if str(item).upper() not in ("NONE", "HELD", "UNKNOWN", "")
        ]

        event: dict[str, Any] = {}
        if (occurred := slot_value("PS_EVENT_DATE")) is not None:
            event["event_date"] = occurred
        for key, slot in (
            ("awareness_date", "PS_AWARENESS_DATE"),
            ("declaration_date", "PS_DECLARATION_DATE"),
        ):
            if (value := slot_value(slot)) is not None:
                event[key] = value
        if peril := slot_value("PS_PERIL"):
            event["cause"] = peril
            event["peril"] = peril
        if (days := slot_value("PS_DAYS_MISSING")) is not None:
            event["days_vehicle_missing"] = days
        if theft_clock := self._theft_clock():
            event["theft_clock"] = theft_clock
        licence = slot_value("PS_LICENSE_STATE")
        if licence is not None:
            token = str(_as_list(licence)[0]) if not isinstance(licence, str) else str(licence)
            if token in LICENCE_DEFEATS_COVER:
                event["valid_licence"] = False
            elif token in LICENCE_HOLDS_COVER:
                event["valid_licence"] = True
        if str(slot_value("PS_INTOXICATION_CAUSAL") or "").lower() == "true":
            event["intoxication_causally_confirmed"] = True
        if fault := self._fault_status():
            event["fault_status"] = fault

        vehicle: dict[str, Any] = {}
        if (market := slot_value("PS_MARKET_VALUE")) is not None:
            vehicle["market_value_at_event_irr"] = irr(market)
        if (insured := slot_value("PS_INSURED_SUM")) is not None:
            vehicle["insured_sum_irr"] = irr(insured)
        if (year := slot_value("PS_PRODUCTION_YEAR")) is not None:
            vehicle["production_year_shamsi"] = year
        if (salvage := slot_value("PS_SALVAGE_VALUE")) is not None:
            vehicle["salvage_value_irr"] = irr(salvage)
        if (disposition := slot_value("PS_SALVAGE_DISPOSITION")) is not None:
            vehicle["salvage_disposition"] = disposition
        if (transferred := slot_value("PS_TITLE_TRANSFERRED")) is not None:
            vehicle["title_transferred"] = str(transferred).lower() == "true"

        damage: dict[str, Any] = {}
        if (theft := slot_value("PS_THEFT_TYPE")) is not None and str(theft) != "NOT_A_THEFT":
            damage["theft_type"] = str(theft)
        if parts:
            damage["parts"] = parts
        for key, slot in (
            ("labor_irr", "PS_LABOR"),
            ("rescue_transport_actual_irr", "PS_RESCUE_ACTUAL"),
            ("gross_damage_irr", "PS_GROSS_DAMAGE"),
            ("repair_total_irr", "PS_REPAIR_TOTAL"),
            ("assessed_depreciation_irr", "PS_ASSESSED_DEPRECIATION"),
        ):
            if (value := slot_value(slot)) is not None:
                damage[key] = irr(value)
        if (rescue_actual := slot_value("PS_RESCUE_ACTUAL")) is not None:
            damage["rescue_for_total_loss_test_irr"] = irr(rescue_actual)
            damage["rescue_for_total_loss_test_source"] = "DERIVED_FROM_ACTUAL_RESCUE"

        config: dict[str, Any] = {}
        for key, slot in (
            ("article10_partial_order", "PS_ARTICLE10_PARTIAL_ORDER"),
            ("battery_tire_depreciation_interaction", "PS_BATTERY_TIRE_INTERACTION"),
            ("rescue_cap_base", "PS_RESCUE_CAP_BASE"),
            ("settlement_mode", "PS_SETTLEMENT_MODE"),
        ):
            value = slot_value(slot)
            if value is not None and str(value) != "UNRESOLVED":
                config[key] = value

        coverage: dict[str, Any] = {}
        for key, slot in (
            ("causal_relationship_established", "PS_CAUSATION_ESTABLISHED"),
            ("glass_from_base_peril", "PS_GLASS_CAUSE_PRECEDENCE"),
        ):
            if (value := slot_value(slot)) is not None:
                coverage[key] = str(value).lower() == "true"
        if str(slot_value("PS_NOTICE_TIMELINESS") or "").lower() == "true":
            coverage["late_notice_issue"] = True
        if str(slot_value("PS_SUBROGATION_IMPAIRED") or "").lower() == "true":
            coverage["subrogation_impaired"] = True
        risk_answer = str(self.answer("Q-S3-07") or "")
        if risk_answer in ("YES", "NO"):
            coverage["risk_intensified"] = risk_answer == "YES"

        evidence = {
            item["node_id"]: item["node_id"] in self.evidence_present()
            for item in self.kb.evidence.values()
        }

        payload: dict[str, Any] = {
            "claim_id": self.claim_id,
            "unit": "IRR",
            "regulatory_snapshot": (
                {"iranian_year": slot_value("PS_CLAIM_YEAR")}
                if slot_value("PS_CLAIM_YEAR") is not None else {}
            ),
            "classification": {},
            "vehicle": vehicle,
            "event": event,
            "damage": damage,
            "policy": {
                "endorsements": endorsements,
                **({"franchise": franchise} if isinstance(franchise, dict) else {}),
                **(
                    {"glass_valuation_condition": slot_value("PS_GLASS_VALUATION_CONDITION")}
                    if slot_value("PS_GLASS_VALUATION_CONDITION") is not None
                    else {}
                ),
                **(
                    {"multiple_insurance": multiple_insurance}
                    if isinstance(multiple_insurance, dict)
                    else {}
                ),
            },
            "evidence": evidence,
            "coverage_gate": coverage,
            "calculation_config": config,
            "derived": (
                {"article10_ratio": slot_value("PS_UNDERINSURANCE_RATIO")}
                if slot_value("PS_UNDERINSURANCE_RATIO") is not None else {}
            ),
        }
        branch = None if getattr(self, "_classification_guard", False) else self.classification().get("branch")
        classification: dict[str, Any] = {}
        domain = self._domain()
        if domain:
            classification["domain"] = domain
        if branch:
            classification["branch"] = branch
        payload["classification"] = classification
        return payload

    def _domain(self) -> str | None:
        """Which calculation family this file belongs to, from the file itself.

        The classifier still derives the *branch*, but the domain must be stated: a
        body claim that also records a fault position would otherwise be mistaken for
        a third-party financial claim, because fault is one of that family's signals.
        """
        answer = str(self.answer("Q-S7-01") or "")
        return {
            "NO_BODY_ONLY": "BODY",
            "PART_OF_IT_ALSO_THIRD_PARTY": "THIRD_PARTY_FINANCIAL",
            "PART_OF_IT_ALSO_LEGAL_RECOVERY": "LEGAL_RECOVERY",
        }.get(answer)

    def _fault_status(self) -> str | None:
        value = self.answer("Q-S2-04")
        return str(value) if value and str(value) != "UNKNOWN" else None

    def evidence_present(self) -> set[str]:
        """Evidence the file records as actually in hand.

        Two channels, both explicit: ``evidence_present`` lists item ids the
        reviewer confirms are in the file, and ``evidence_received`` does the same
        for a form that only ticks documents off. Nothing here infers that a
        document exists because a question was answered.
        """
        present: set[str] = set()
        for key in ("evidence_present", "evidence_received"):
            present.update(str(item) for item in _as_list(self.payload.get(key)))
        return present

    # ------------------------------------------------------------ classification

    def classification(self) -> dict[str, Any]:
        cache = getattr(self, "_classification_cache", None)
        if cache is not None:
            return cache
        payload = self.case_payload_without_branch()
        try:
            verdict = classify(payload, self.kb)
        except Exception as error:  # an incomplete file is not a crash
            verdict = {
                "branch": None,
                "variant": None,
                "confidence": 0.0,
                "basis": [f"cannot classify yet: {type(error).__name__}: {error}"],
            }
        self._classification_cache = verdict
        return verdict

    def case_payload_without_branch(self) -> dict[str, Any]:
        self._classification_guard = True
        try:
            payload = self.case_payload()
        finally:
            self._classification_guard = False
        payload.get("classification", {}).pop("branch", None)
        return payload

    # ------------------------------------------------------------------- ladder

    def tier(self) -> dict[str, Any]:
        """The highest rung whose gate this file satisfies.

        A tier whose gate is `always` is the fallback (T6), not a competitor: without
        that distinction every file would "reach" the uncertified rung and the ladder
        would report the worst case for the best one.
        """
        branch = self.classification().get("branch")
        matched: list[dict[str, Any]] = []
        fallback: dict[str, Any] | None = None
        for node in self.kb.ordered_tiers():
            reachable = node.get("reachable_branches") or []
            if branch and reachable and branch not in reachable:
                continue
            if not self.holds(node.get("gate")):
                continue
            entry = {
                "tier": node["node_id"],
                "name": node.get("name"),
                "purpose": node.get("purpose"),
                "permitted_outcomes": node.get("permitted_outcomes"),
                "calibration_needed": node.get("calibration_needed"),
                "must_not": node.get("must_not"),
                "exit_evidence": node.get("exit_evidence"),
            }
            if (node.get("gate") or {}).get("always"):
                fallback = entry
            else:
                matched.append(entry)
        top = matched[-1] if matched else fallback
        return {
            "assigned": top["tier"] if top else None,
            "name": top["name"] if top else None,
            "permitted_outcomes": top["permitted_outcomes"] if top else [],
            "candidates": [entry["tier"] for entry in matched],
            "certified": bool(matched),
            "branch": branch,
            "detail": top,
        }

    # ---------------------------------------------------------------- questions

    def next_questions(self, limit: int | None = None) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for question in self.kb.ordered_questions():
            if self.is_answered(question["node_id"]):
                continue
            when = question.get("when")
            if when and not self.holds(when):
                continue
            out.append(
                {
                    "id": question["node_id"],
                    "stage": question.get("stage"),
                    "ask": question.get("ask"),
                    "ask_fa": question.get("ask_fa"),
                    "format": question.get("answer_format"),
                    "answers": question.get("answers"),
                    "blocking": question.get("blocking"),
                    "tier": question.get("tier"),
                    "why": question.get("why"),
                    "evidence": [
                        self.kb.evidence_item(item)["name"] if self.kb.evidence_item(item) else item
                        for item in question.get("requires_evidence") or []
                    ],
                }
            )
            if limit and len(out) >= limit:
                break
        return out

    def blocking_unanswered(self) -> list[str]:
        return [
            item["id"]
            for item in self.next_questions()
            if item["blocking"] in ("hard", "amount") and item["stage"] != "S10_QUALITY_GATE"
        ]

    def stage_progress(self) -> list[dict[str, Any]]:
        rows = []
        for stage in self.kb.ordered_stages():
            questions = self.kb.questions_for_stage(stage["node_id"])
            answered: list[str] = []
            open_now: list[str] = []
            not_applicable: list[str] = []
            for question in questions:
                if self.is_answered(question["node_id"]):
                    answered.append(question["node_id"])
                    continue
                when = question.get("when")
                if when and not self.holds(when):
                    not_applicable.append(question["node_id"])
                else:
                    open_now.append(question["node_id"])
            rows.append(
                {
                    "stage": stage["node_id"],
                    "order": stage.get("order"),
                    "name": stage.get("name"),
                    "answered": len(answered),
                    "open": open_now,
                    "not_applicable": not_applicable,
                    "total": len(questions),
                    "closes_when": stage.get("closes_when"),
                }
            )
        return rows

    # ----------------------------------------------------------------- readiness

    def missing_evidence(self) -> list[dict[str, str]]:
        """Evidence this file now requires and does not hold.

        An item is demanded only when its own `required_when` says so: a "no" answer
        to the intoxication question must not conjure a court file into the checklist.
        Items with no condition are demanded by the branch or by the question that was
        actually answered.
        """
        present = self.evidence_present()
        branch = self.classification().get("branch")

        def demanded(item_id: str) -> bool:
            node = self.kb.evidence_item(item_id)
            if node is None:
                return False
            condition = node.get("required_when")
            return self.holds(condition) if condition else True

        wanted: dict[str, dict[str, str]] = {}
        for item_id in (self.kb.branch(branch) or {}).get("required_evidence") or []:
            if demanded(item_id):
                entry = self.kb.evidence_item(item_id)
                wanted[item_id] = _evidence_row(entry, "the branch requires it")
        for question in self.kb.ordered_questions():
            if not self.is_answered(question["node_id"]):
                continue
            when = question.get("when")
            if when and not self.holds(when):
                continue
            for item_id in question.get("requires_evidence") or []:
                if item_id in wanted or not demanded(item_id):
                    continue
                entry = self.kb.evidence_item(item_id)
                wanted[item_id] = _evidence_row(entry, f"required by {question['node_id']}")
        return [entry for item_id, entry in sorted(wanted.items()) if item_id not in present]

    def open_uncertainties(self) -> list[str]:
        return sorted(
            node["node_id"] for node in self.kb.uncertainties.values() if self.uncertainty_is_live(node["node_id"])
        )

    def _risk_intensification_resolved(self) -> bool:
        """Whether the premium-ratio reduction demanded by U15 can be applied.

        The regulation reduces payment by the ratio of the premium charged to the
        premium appropriate to the intensified risk. No parameter slot or claim-case
        field carries either premium, and no insurer adapter supplies one, so the
        operator is unresolvable today. ``U15`` records
        ``NOT_IMPLEMENTED_DO_NOT_SUBSTITUTE``: escalating is correct, approximating
        it with the underinsurance ratio is not.

        This is the extension point for the first insurer adapter - once the
        charged and tariff premiums become sourced slots, resolve them here and
        the file may proceed to calculation.
        """
        return False

    def _eligibility_blocking_conditions(self, branch: str | None) -> list[str]:
        """Contain IA-01/02 before an immutable authorization can be issued."""
        if branch not in ("PARTIAL_DAMAGE", "TOTAL_LOSS", "GLASS_ONLY", "THEFT"):
            return []

        conditions: list[str] = []
        causation = str(self.answer("Q-S2-02") or "").upper()
        if causation == "ASSERTED_ONLY":
            conditions.append("COVERED_PERIL_CAUSATION_NOT_ESTABLISHED")

        recovery = self._bound.get("PS_MULTIPLE_POLICIES")
        if isinstance(recovery, dict):
            prior = recovery.get("prior_compensation")
            if prior is not None and money.D(prior) > 0:
                conditions.append("PRIOR_COMPENSATION_SETTLEMENT_UNSUPPORTED")
            if str(recovery.get("state") or "").upper() in (
                "YES_OTHER_POLICIES",
                "YES_SAME_INSURER",
            ):
                conditions.append("MULTIPLE_INSURANCE_CONTRIBUTION_NOT_IMPLEMENTED")
        if (
            branch == "TOTAL_LOSS"
            and self._bound.get("PS_SALVAGE_DISPOSITION") == "INSURER_TAKES_TITLE"
            and str(self._bound.get("PS_TITLE_TRANSFERRED") or "").lower() != "true"
        ):
            conditions.append("TITLE_TRANSFER_REQUIRED")
        return conditions

    def decision(self) -> dict[str, Any]:
        """What the pipeline may issue now. This is the only gate that answers it."""
        classification = self.classification()
        branch = classification.get("branch")
        blocking_open = self.blocking_unanswered()
        hard_open = [
            item
            for item in blocking_open
            if (self.kb.question(item) or {}).get("blocking") == "hard"
        ]
        refused_by = self.refusal_reasons()

        evidence_blocks = self.stopping_evidence()
        blocking_conditions = self._eligibility_blocking_conditions(branch)
        if str(self.answer("Q-S0-06") or "").upper() == "INSTALMENT_OVERDUE":
            blocking_conditions.append("POLICY_CANCELLATION_STATUS_UNRESOLVED")
        if self.uncertainty_is_live("U13_THEFT_CLOCK_ANCHOR"):
            blocking_conditions.append("THEFT_CLOCK_ANCHOR_UNRESOLVED")
        if self.uncertainty_is_live("U15_RISK_INTENSIFICATION_PREMIUM_RATIO") and not (
            self._risk_intensification_resolved()
        ):
            blocking_conditions.append("RISK_INTENSIFICATION_PREMIUM_RATIO_UNRESOLVED")

        if refused_by:
            kind = DECISION_REFUSE
        elif (
            branch is None
            or self.has_blocking_questions(blocking_open)
            or evidence_blocks
            or blocking_conditions
        ):
            kind = DECISION_INSUFFICIENT
        elif self.open_uncertainties():
            kind = DECISION_SCENARIO
        else:
            kind = DECISION_COMPUTE

        return {
            "decision": kind,
            "branch": branch,
            "classification_confidence": classification.get("confidence"),
            "tier": self.tier()["assigned"],
            "refused_by": refused_by,
            "open_hard_questions": hard_open,
            "open_blocking_questions": blocking_open,
            "evidence_blocks": evidence_blocks,
            "blocking_conditions": blocking_conditions,
            "live_uncertainties": self.open_uncertainties(),
            "missing_evidence": [entry["item"] for entry in self.missing_evidence()],
        }

    def stopping_evidence(self) -> list[str]:
        """Demanded documents whose absence must stop calculation.

        ``ROUTE_TO_REVIEW`` stays on the report. ``REDUCE_CONFIDENCE`` still
        calculates, under ``evidence_confidence_cap``.
        """
        return [
            entry["item"]
            for entry in self.missing_evidence()
            if entry.get("if_absent") in STOPPING_IF_ABSENT
        ]

    def evidence_confidence_cap(self) -> Decimal | None:
        """Lowest ``confidence_if_absent`` among missing REDUCE_CONFIDENCE items."""
        caps: list[Decimal] = []
        for entry in self.missing_evidence():
            if entry.get("if_absent") != "REDUCE_CONFIDENCE":
                continue
            node = self.kb.evidence_item(entry["item"]) or {}
            raw = node.get("confidence_if_absent")
            if raw is None:
                continue
            caps.append(money.D(raw))
        return min(caps) if caps else None

    def has_blocking_questions(self, blocking_open: list[str] | None = None) -> bool:
        """Whether an unanswered question prevents a calculation handoff.

        ``hard`` questions prevent classification and ``amount`` questions leave an
        engine input unset. Both stop the handoff. Treating only the first group as
        blocking allowed a missing production year to become zero depreciation and
        allowed a missing franchise to become a misleading scenario decision.
        """
        blocking_open = blocking_open if blocking_open is not None else self.blocking_unanswered()
        return any(
            (self.kb.question(item) or {}).get("blocking") in ("hard", "amount")
            for item in blocking_open
        )

    def refusal_reasons(self) -> list[str]:
        """Coverage-gate answers that stop the file before arithmetic."""
        reasons: list[str] = []
        if str(self.answer("Q-S0-06") or "").upper() == "LAPSED":
            reasons.append("policy not in force on the event date (Q-S0-06)")
        if str(self.answer("Q-S1-03") or "").upper() == "OUTSIDE_NO_AGREEMENT":
            reasons.append("loss outside the territorial scope with no special agreement (Q-S1-03)")
        if str(self.answer("Q-S2-02") or "").upper() == "CONTRADICTED":
            reasons.append("the stated peril is contradicted by the evidence (Q-S2-02)")
        if str(self.answer("Q-S3-03") or "").upper() in ("YES_INTENTIONAL", "YES_FLIGHT"):
            reasons.append("a non-compensable cause is present (Q-S3-03)")
        if str(self.answer("Q-S3-04") or "").upper() in ("WAR_OR_NUCLEAR", "UNAUTHORIZED_TOWING", "OVERLOAD", "INHERENT_ELECTRICAL"):
            reasons.append(f"non-compensable condition {self.answer('Q-S3-04')} (Q-S3-04)")
        if (licence := str(self.answer("Q-S3-01") or "").upper()) in LICENCE_DEFEATS_COVER:
            reasons.append(f"licence state {licence} defeats cover (Q-S3-01)")
        if str(self.answer("Q-S3-02") or "").upper() == "CONFIRMED_AND_CAUSAL":
            reasons.append("intoxication confirmed by a competent authority and causal (Q-S3-02)")
        if str(self.answer("Q-S3-08") or "").upper() == "YES":
            reasons.append("ownership transferred after an undeclared accident (Q-S3-08)")
        if str(self.answer("Q-S7-01") or "").upper() == "UNKNOWN":
            reasons.append("the file has not established whether part of the loss belongs to another branch (Q-S7-01)")
        return reasons

    # ------------------------------------------------------------------- engine

    def authorize(self) -> CalculationAuthorization:
        """Issue the only authorization a claim file can obtain.

        The review decision is the gate: REFUSE and INSUFFICIENT_INFORMATION are
        terminal and raise instead of producing an authorization, so no path from
        a reviewed file can reach the calculator without the file first passing.

        The authorization owns immutable canonical claim and provenance snapshots.
        ``compute()`` materializes a fresh validated ``Case`` from that snapshot,
        so no mutable review or ``Case`` object remains authoritative after issue.
        """
        decision = self.decision()
        kind = decision["decision"]
        if kind not in AUTHORIZED_DECISIONS:
            raise AuthorizationNotGranted(
                f"review decision {kind} does not authorize calculation"
                + (
                    f"; refused by {decision['refused_by']}"
                    if decision["refused_by"]
                    else ""
                )
                + (
                    f"; unresolved: {', '.join(decision['blocking_conditions'])}"
                    if decision["blocking_conditions"]
                    else ""
                )
            )

        payload = self.case_payload()
        case = validated_case(payload)
        classification, _, _ = reconcile_classification(case, self.kb)
        snapshot = self.kb.resolve_snapshot(case.event_date, case.claim_year)

        return _issue_review_authorization(
            payload,
            decision=kind,
            issued_at=utc_now(),
            provenance={
                "review_kind": self.authorization_kind,
                "claim_id": self.claim_id,
                "branch": decision["branch"],
                "tier": decision["tier"],
                "reviewer": str(self.payload.get("reviewed_by") or self.answer("Q-S10-01") or ""),
                "review_as_of": str(self.payload.get("as_of") or "") or None,
                "classification": classification,
                "snapshot_id": (snapshot or {}).get("snapshot_id"),
                "live_uncertainties": list(decision["live_uncertainties"]),
                "blocking_conditions": list(decision["blocking_conditions"]),
                "missing_evidence": list(decision["missing_evidence"]),
                "evidence_confidence_cap": (
                    str(self.evidence_confidence_cap())
                    if self.evidence_confidence_cap() is not None
                    else None
                ),
                "policy_snapshot": {
                    "policy_version": case.policy.get("policy_version"),
                    "insurer": case.policy.get("insurer"),
                    "endorsements": sorted(case.endorsement_tokens()),
                    "franchise": case.policy_franchise,
                },
                "approved_overrides": (
                    [classification["override"]] if classification.get("override") else []
                ),
            },
        )

    def calculate(self) -> CalcResult | None:
        """Run the engine only when this file authorizes calculation."""
        if self.decision()["decision"] not in AUTHORIZED_DECISIONS:
            return None
        return compute(self.authorize(), self.kb)

    # ------------------------------------------------------------------ report

    def to_json(self) -> dict[str, Any]:
        result = self.calculate()
        return {
            "claim_id": self.claim_id,
            "unit": self.unit,
            "decision": self.decision(),
            "tier": self.tier(),
            "classification": self.classification(),
            "stage_progress": self.stage_progress(),
            "next_questions": self.next_questions(),
            "parameters": [binding.to_dict() for binding in self.slots_for(
                self.classification().get("branch") or "PARTIAL_DAMAGE"
            )],
            "missing_evidence": self.missing_evidence(),
            "live_uncertainties": self.open_uncertainties(),
            "refusal_reasons": self.refusal_reasons(),
            "calculation": result.to_dict() if result else None,
            "case_payload": self.case_payload() if self.classification().get("branch") else None,
        }

    def report(self) -> str:
        decision = self.decision()
        tier = self.tier()
        lines: list[str] = []
        add = lines.append

        add("CASE REVIEW - بیمه بدنه (body / monetary damage to the insured vehicle)")
        add(f"  Claim : {self.claim_id}   unit: {self.unit}")
        add(f"  Branch: {decision['branch'] or 'not yet derivable'}"
            f"   classification confidence: {decision['classification_confidence']}")
        add(f"  Tier  : {tier['assigned'] or 'uncertified'} - {tier['name'] or 'no rung matched'}")
        add(f"  ISSUE : {decision['decision']}")
        add("")

        add("STAGES")
        for row in self.stage_progress():
            tally = f"{row['answered']}/{row['total'] - len(row['not_applicable'])}"
            add(f"  {row['stage']:<22}{tally:>8}  {row['name']}")
            if row["open"]:
                shown = ", ".join(row["open"][:5]) + (", …" if len(row["open"]) > 5 else "")
                add(f"      still open : {shown}")
            if row["not_applicable"]:
                add(f"      not asked  : {len(row['not_applicable'])} question(s) gated off by earlier answers")
        add("")

        if decision["refused_by"]:
            add("REFUSALS ESTABLISHED BY THE FILE")
            for reason in decision["refused_by"]:
                add(f"  - {reason}")
            add("")

        if decision["blocking_conditions"]:
            add("UNRESOLVED ACCEPTANCE CONDITIONS")
            for condition in decision["blocking_conditions"]:
                add(f"  - {condition}")
            add("")

        nxt = self.next_questions(limit=8)
        if nxt:
            add("NEXT QUESTIONS")
            for item in nxt:
                mark = {"hard": "[blocking]", "amount": "[amount]", "review": "[review]"}.get(
                    item["blocking"], "[optional]"
                )
                add(f"  {item['id']} {mark} ({item['stage']}, tier {item['tier']})")
                add(f"      {item['ask']}")
                if item["answers"]:
                    add(f"      answers: {', '.join(str(a) for a in item['answers'])}")
                if item["evidence"]:
                    add(f"      evidence: {'; '.join(item['evidence'])}")
                add(f"      why: {item['why']}")
            add("")

        add("PARAMETERS FOR THIS BRANCH")
        for binding in self.slots_for(decision["branch"] or "PARTIAL_DAMAGE"):
            value = "" if binding.value in (None, "") else f" = {_brief(binding.value)}"
            add(f"  {binding.status:<12}{binding.slot_id}{value}")
            if binding.status != STATUS_RESOLVED:
                add(f"      select : {binding.select}")
                add(f"      source : {'/'.join(binding.supplied_via) or 'unspecified'}"
                    f"  authority: {binding.authority}")
                if binding.blocking_uncertainty:
                    add(f"      blocks : {binding.blocking_uncertainty}")
        add("")

        missing = self.missing_evidence()
        if missing:
            add("EVIDENCE STILL MISSING")
            for entry in missing:
                add(f"  - {entry['item']} ({entry['source_class']}): {entry['name']}  [{entry['why']}]")
                add(f"      if absent: {entry['if_absent']}")
            add("")

        if decision["live_uncertainties"]:
            add("LIVE UNRESOLVED VARIABLES")
            for uncertainty_id in decision["live_uncertainties"]:
                node = self.kb.uncertainty(uncertainty_id)
                add(f"  {uncertainty_id}: {node.get('question')}")
                add(f"      resolves with: {node.get('resolution_artefact')}")
            add("")

        result = self.calculate()
        if result is not None:
            add("CALCULATION")
            if result.payable is not None:
                add(f"  payable: {money.fmt(result.payable, 'million_toman')}")
            for index, value in enumerate(result.payable_scenarios):
                add(f"  scenario {chr(ord('A') + index)}: {money.fmt(value, 'million_toman')}")
            add(f"  status : {result.status or 'SETTLED'}   confidence: {result.formula_confidence}")
            if result.labels:
                add(f"  labels : {', '.join(sorted(result.labels))}")
            if result.rule_trace:
                add(f"  trace  : {', '.join(result.rule_trace)}")
            add("")

        add("AUTHORITY BOUNDARY")
        add("  This layer selects parameters; it does not create them. Every rate, order and")
        add("  cap must already exist in the knowledge graph and must name its own source.")
        return "\n".join(lines)


def _evidence_row(node: dict[str, Any], why: str) -> dict[str, str]:
    item_id = node.get("node_id", "?")
    return {
        "item": item_id,
        "name": node.get("name", item_id),
        "source_class": node.get("source_class", ""),
        "if_absent": node.get("if_absent", ""),
        "why": why,
    }


def _merge_object(current: Any, value: Any, field: Any) -> dict[str, Any]:
    """Fold one answer into an object-valued slot.

    Franchise terms arrive in pieces - the mode from one question, the rate from
    another, the source version from a third - and each piece has to accumulate into
    a single policy-shaped object the engine already understands. A string answer
    with no field name is treated as the mode, because that is how the schedule is
    read first.
    """
    if isinstance(current, dict):
        merged = dict(current)
    elif isinstance(current, str) and current:
        merged = {"mode": current}
    else:
        merged = {}
    if isinstance(value, dict):
        merged.update(value)
    else:
        merged[str(field or "mode")] = value
    return merged


def _brief(value: Any, limit: int = 70) -> str:
    text = json.dumps(value, ensure_ascii=False, default=str) if isinstance(value, (list, dict)) else str(value)
    return text if len(text) <= limit else text[: limit - 1] + "…"


# --------------------------------------------------------------------- artefacts
#
# These generators are the single source of the flowchart and the tables in
# docs/BODY_CASE_REVIEW_MODEL.md. `tests/test_review.py` regenerates them and
# compares against the document, so prose can never drift from the data.


def _q(text: str) -> str:
    """Quote a mermaid label so punctuation inside it stays inert."""
    return '"' + text.replace('"', "'") + '"'


def mermaid_flowchart(kb: Knowledge) -> str:
    """Acceptance pipeline: stages, then the one gate that may issue a result.

    Body branches are not drawn here. Each used to repeat the same three exits,
    which hid the gate. Branch selection is ``mermaid_branch_tree``.
    """
    lines = ["```mermaid", "flowchart TD"]
    lines.append(f"  START {_q('Claim file opened')} --> S0 {_q('0. Establish the file')}")
    previous = "S0"
    for stage in kb.ordered_stages():
        node_id = stage["node_id"].split("_", 1)[0]
        if node_id == "S0":
            continue
        label = "%s. %s" % (stage["order"], stage["name"])
        lines.append("  %s --> %s %s" % (previous, node_id, _q(label)))
        previous = node_id

    lines.append('  %s --> GATE {"Decision gate"}' % previous)
    lines.append(f"  GATE -- cover defeated --> REFUSE {_q('REFUSE: name the provision, run no arithmetic')}")
    lines.append(f"  GATE -- a required question is open --> INSUF {_q('INSUFFICIENT_INFORMATION: print the question')}")
    lines.append(f"  GATE -- a blocking uncertainty is live --> SCEN {_q('SCENARIO_SET: do not pick or average')}")
    lines.append(f"  GATE -- classified and sourced --> RUN {_q('COMPUTE: hand the case to the engine')}")
    lines.append(f"  REFUSE --> TRACE {_q('Trace: rules, provenance, confidence')}")
    lines.append("  INSUF --> TRACE")
    lines.append("  SCEN --> TRACE")
    lines.append("  RUN --> TRACE")
    lines.append("```")
    return "\n".join(lines)


def _link(src: str, dst: str, via: str | None = None) -> str:
    if via:
        return f'  {src} -- "{via}" --> {dst}'
    return f"  {src} --> {dst}"


def mermaid_architecture(kb: Knowledge) -> str:
    """Repository execution path, from sources to a traced result."""
    del kb  # the path is the runtime, not a projection of one node class
    nodes = [
        ("SRC", "Sources"),
        ("RULE", "LegalRule, Circular, or Policy"),
        ("KG", "Knowledge graph"),
        ("OG", "Operator graph"),
        ("VAL", "Validation gate"),
        ("REV", "Review decision"),
        ("ENG", "Calculation engine"),
        ("OUT", "Result, provenance, confidence, uncertainty"),
    ]
    lines = ["```mermaid", "flowchart TD"]
    lines.extend(f"  {node_id} {_q(label)}" for node_id, label in nodes)
    chain = ["SRC", "RULE", "KG", "OG", "VAL", "REV"]
    for left, right in zip(chain, chain[1:]):
        lines.append(_link(left, right))
    lines.append(_link("REV", "ENG", "COMPUTE or SCENARIO_SET"))
    lines.append(_link("REV", "OUT", "REFUSE or INSUFFICIENT"))
    lines.append(_link("ENG", "OUT"))
    lines.append("```")
    return "\n".join(lines)


def mermaid_branch_tree(kb: Knowledge) -> str:
    """Body-branch selection after the cover gate.

    A failed 75% test is not yet partial damage: standalone glass is still open.
    The theft-clock anchor must be sourced; declaration also starts a separate
    payment period.
    """
    del kb
    nodes = [
        ("CLAIM", "Cover gate passed"),
        ("RECON", "Reconcile a declared branch with the evidence"),
        ("REFUSE", "REFUSE before arithmetic"),
        ("THEFT", "Theft?"),
        ("CLOCK", "60-day clock under the sourced anchor, and title transferred?"),
        ("PENDING", "PENDING_60_DAY_CRITERION"),
        ("TITLE", "TITLE_TRANSFER_REQUIRED"),
        ("TSET", "Theft total settlement"),
        ("EXCL", "Exclusion unless that endorsement is read"),
        ("TERMS", "INSUFFICIENT: endorsement terms"),
        ("TOTAL", "Repair + replacement + rescue above 75% of day value?"),
        ("TLOSS", "Total loss settlement"),
        ("GLASS", "Standalone glass?"),
        ("GCALC", "Glass calculation, depreciation zero"),
        ("INSUF", "INSUFFICIENT_INFORMATION"),
        ("PARTIAL", "Partial damage"),
    ]
    links = [
        ("CLAIM", "RECON", None),
        ("RECON", "REFUSE", "contradicts the evidence"),
        ("RECON", "THEFT", "agrees, or none declared"),
        ("THEFT", "CLOCK", "whole vehicle"),
        ("CLOCK", "PENDING", "under 60 days"),
        ("CLOCK", "TITLE", "at least 60 days, no title"),
        ("CLOCK", "TSET", "at least 60 days and title transferred"),
        ("THEFT", "PARTIAL", "attempted theft"),
        ("THEFT", "EXCL", "parts after the accident"),
        ("THEFT", "TERMS", "partial parts theft"),
        ("THEFT", "TOTAL", "not a theft"),
        ("TOTAL", "TLOSS", "above 75%"),
        ("TOTAL", "GLASS", "not total"),
        ("GLASS", "GCALC", "endorsement read"),
        ("GLASS", "INSUF", "wording missing"),
        ("GLASS", "PARTIAL", "with other damage, or not glass"),
    ]
    lines = ["```mermaid", "flowchart TD"]
    lines.extend(f"  {node_id} {_q(label)}" for node_id, label in nodes)
    lines.extend(_link(src, dst, via) for src, dst, via in links)
    lines.append("```")
    return "\n".join(lines)


def questionnaire_markdown(kb: Knowledge) -> str:
    """The procedure as a table, one row per question, in the order it is asked."""
    rows = [
        "| # | Ask | Admissible answers | Binds | Evidence | Blocking | Rung |",
        "|---|---|---|---|---|---|---|",
    ]
    for question in kb.ordered_questions():
        bindings = ", ".join(
            str(binding.get("slot"))
            for binding in question.get("sets") or []
            if isinstance(binding, dict)
        ) or "-"
        evidence = ", ".join(str(item) for item in question.get("requires_evidence") or []) or "-"
        answers = ", ".join(str(item) for item in question.get("answers") or []) or question.get("answer_format", "")
        when = ""
        if question.get("when"):
            when = f" _(asked when: `{json.dumps(question['when'], ensure_ascii=False)}`)_"
        rows.append(
            f"| {question['node_id']} | {question.get('ask')}{when} | {answers} | {bindings} | "
            f"{evidence} | {question.get('blocking')} | {question.get('tier')} |"
        )
    return "\n".join(rows)


def parameters_markdown(kb: Knowledge) -> str:
    """What each parameter is, who may supply it, and what happens when nobody does."""
    rows = [
        "| Slot | Unit | Authority | Supplied by | Absent means | Uncertainty | Guardrail | Branches |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for slot_id, node in sorted(kb.slots.items()):
        questions = ", ".join(q["node_id"] for q in kb.questions_filling_slot(slot_id)) or "-"
        rows.append(
            f"| {slot_id} | {node.get('unit')} | {node.get('authority')} | {questions} | "
            f"{node.get('missing_behavior')} | {node.get('blocking_uncertainty') or '-'} | "
            f"{node.get('guardrail') or '-'} | {', '.join(node.get('required_for_branches') or []) or '-'} |"
        )
    return "\n".join(rows)


def ladder_markdown(kb: Knowledge) -> str:
    rows = [
        "| Rung | Adds | Permitted outcomes | Corpus | Calibration still needed |",
        "|---|---|---|---|---|",
    ]
    for node in kb.ordered_tiers():
        rows.append(
            f"| {node['node_id']} {node.get('name')} | {node.get('purpose')} | "
            f"{', '.join(node.get('permitted_outcomes') or [])} | "
            f"{', '.join(node.get('example_cases') or []) or '-'} | "
            f"{', '.join(node.get('calibration_needed') or []) or 'nothing - complete as certified'} |"
        )
    return "\n".join(rows)
