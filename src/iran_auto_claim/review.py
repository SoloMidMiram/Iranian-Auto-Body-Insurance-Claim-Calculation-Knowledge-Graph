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
3. **Money answers are in the case's declared unit**, exactly like the worked
   examples in ``cases/``, and the key names keep the shape the engine reads.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from . import money
from .case import PART_CATEGORIES
from .classify import classify
from .engine import CalcResult, compute
from .knowledge import Knowledge

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

    def __init__(self, payload: dict[str, Any], kb: Knowledge | None = None) -> None:
        if not isinstance(payload, dict):
            raise ReviewInputError("a review payload must be a JSON object")
        self.kb = kb or Knowledge.load()
        self.claim_id = str(payload.get("claim_id") or payload.get("id") or "unnamed-review")
        self.unit = payload.get("unit") or "million_toman"
        self.payload = payload
        self.answers: dict[str, Any] = dict(payload.get("answers") or {})
        self._validate_answers()
        self.slots: dict[str, SlotBinding] = {}
        self._bound: dict[str, Any] = {}
        self.bind()

    @classmethod
    def from_file(cls, path: Path | str, kb: Knowledge | None = None) -> "Review":
        return cls(json.loads(Path(path).read_text(encoding="utf-8")), kb)

    # ------------------------------------------------------------------ answers

    def _validate_answers(self) -> None:
        for question_id, value in self.answers.items():
            question = self.kb.question(question_id)
            if question is None:
                raise ReviewInputError(
                    f"{question_id!r} is not a question in the procedure; "
                    "the answer vocabulary is closed"
                )
            allowed = {str(item) for item in question.get("answers") or []}
            fmt = question.get("answer_format")
            if fmt in ("choice", "list_of_choices"):
                for item in _as_list(value):
                    if str(item) == "UNKNOWN" or str(item) in allowed:
                        continue
                    raise ReviewInputError(
                        f"{question_id}: {item!r} is not admissible; expected "
                        f"{', '.join(sorted(allowed))} or UNKNOWN"
                    )
            if fmt == "money" and not _is_number(value):
                raise ReviewInputError(f"{question_id}: {value!r} is not a money amount")
            if fmt == "integer" and not isinstance(value, int):
                raise ReviewInputError(f"{question_id}: {value!r} is not an integer")

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

    def bind(self) -> None:
        """Run every question's bindings in procedure order."""
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
            value = int(money.D(value))
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
        """Run every question's bindings in procedure order."""
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

    def _derive_dependent_slots(self) -> None:
        """Recompute the slots that are functions of other slots, never of opinions.

        The underinsurance ratio is the only one the calculation actually needs from
        the review layer, and it is the one value an adjuster most often mis-states,
        so it is derived here from the two evidenced figures rather than asked.
        """
        market = self._bound.get("PS_MARKET_VALUE")
        insured = self._bound.get("PS_INSURED_SUM")
        if market and insured:
            self._bound["PS_UNDERINSURANCE_RATIO"] = float(
                min(Decimal(1), money.D(insured) / money.D(market))
            )
        # An itemised assessment *is* the repair-and-replacement figure the total-loss
        # test needs; deriving it keeps the 75% test from silently skipping.
        if self._bound.get("PS_REPAIR_TOTAL") is None:
            records = [item for item in _as_list(self._bound.get("PS_PART_CATEGORY")) if isinstance(item, dict)]
            if records:
                total = sum(money.D(item.get("assessed_loss", item.get("assessed_loss_irr", 0)) or 0) for item in records)
                total += money.D(self._bound.get("PS_LABOR") or 0)
                self._bound["PS_REPAIR_TOTAL"] = int(total)
                if self._bound.get("PS_GROSS_DAMAGE") is None:
                    self._bound["PS_GROSS_DAMAGE"] = int(total)

    def _derive(self, slot_id: str, derivation: str) -> None:
        if derivation == "iranian_year_of_event":
            raw = str(self.answer("Q-S0-02") or "")
            year = int(raw[:4]) if raw[:4].isdigit() else None
            if year is not None and 1300 <= year <= 1500:
                self._bound[slot_id] = year
        elif derivation == "underinsurance_ratio":
            market = self._bound.get("PS_MARKET_VALUE")
            insured = self._bound.get("PS_INSURED_SUM")
            if market and insured:
                self._bound[slot_id] = min(1.0, float(insured) / float(market))

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
            special = any(str(item.get("category")) in ("BATTERY", "TIRE") for item in parts)
            year = slot("PS_PRODUCTION_YEAR")
            claim_year = slot("PS_CLAIM_YEAR") or self.kb.annual_raw.get("default_year", 1405)
            index = (int(claim_year) - int(year) + 1) if year else 0
            return special and index >= 5
        if uncertainty_id == "U05_RESCUE_DENOMINATOR":
            return _is_number(slot("PS_RESCUE_ACTUAL")) and money.D(slot("PS_RESCUE_ACTUAL")) > 0
        if uncertainty_id == "U12_SALVAGE_DISPOSITION":
            return str(slot("PS_SALVAGE_DISPOSITION") or "") == "UNRESOLVED"
        if uncertainty_id == "U13_THEFT_CLOCK_ANCHOR":
            days = slot("PS_DAYS_MISSING")
            return str(slot("PS_THEFT_TYPE") or "") == "WHOLE_VEHICLE" and isinstance(days, int) and 55 <= days <= 65
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
        if mode.startswith("PERCENT"):
            return franchise.get("rate") is not None and franchise.get("source") in (
                "POLICY",
                "ENDORSEMENT",
                "INSURER_MANUAL",
            )
        return franchise.get("absolute_irr") is not None or franchise.get("absolute") is not None

    # ------------------------------------------------------------ case emission

    def case_payload(self) -> dict[str, Any]:
        """The schema-shaped case a completed review hands to the engine."""
        slot_value = lambda key: self._bound.get(key)  # noqa: E731

        def part_records() -> list[dict[str, Any]]:
            records = []
            for item in _as_list(slot_value("PS_PART_CATEGORY")):
                if isinstance(item, dict):
                    category = str(item.get("category") or "OTHER_REPLACEMENT_PART")
                    records.append(
                        {
                            "name": item.get("name"),
                            "category": category,
                            "assessed_loss_irr": item.get("assessed_loss", item.get("assessed_loss_irr", 0)),
                            "new_price_irr": item.get("new_price", item.get("new_price_irr")),
                            "requires_replacement": bool(item.get("requires_replacement", True)),
                        }
                    )
                elif str(item) in PART_CATEGORIES:
                    records.append({"category": str(item), "assessed_loss_irr": 0})
            return records

        parts = part_records()
        new_price = slot_value("PS_PART_NEW_PRICE")
        if new_price is not None:
            for record in parts:
                if record["category"] in ("BATTERY", "TIRE") and record.get("new_price_irr") in (None, 0):
                    record["new_price_irr"] = new_price

        franchise = slot_value("PS_FRANCHISE")
        endorsements = [
            str(item).upper()
            for item in _as_list(slot_value("PS_ENDORSEMENTS"))
            if str(item).upper() not in ("NONE", "HELD", "UNKNOWN", "")
        ]

        event: dict[str, Any] = {"event_date": slot_value("PS_EVENT_DATE")}
        if peril := slot_value("PS_PERIL"):
            event["cause"] = peril
            event["peril"] = peril
        if theft := slot_value("PS_THEFT_TYPE"):
            if str(theft) != "NOT_A_THEFT":
                event["theft_type"] = str(theft)
        if days := slot_value("PS_DAYS_MISSING"):
            event["days_vehicle_missing"] = days
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
            vehicle["market_value_at_event_irr"] = market
        if (insured := slot_value("PS_INSURED_SUM")) is not None:
            vehicle["insured_sum_irr"] = insured
        if (year := slot_value("PS_PRODUCTION_YEAR")) is not None:
            vehicle["production_year_shamsi"] = year
        if (salvage := slot_value("PS_SALVAGE_VALUE")) is not None:
            vehicle["salvage_value_irr"] = salvage
        if (disposition := slot_value("PS_SALVAGE_DISPOSITION")) is not None:
            vehicle["salvage_disposition"] = disposition
        if str(slot_value("PS_TITLE_TRANSFERRED") or "").lower() == "true":
            vehicle["title_transferred"] = True

        damage: dict[str, Any] = {}
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
                damage[key] = value

        config: dict[str, Any] = {}
        for key, slot in (
            ("article10_partial_order", "PS_ARTICLE10_PARTIAL_ORDER"),
            ("battery_tire_depreciation_interaction", "PS_BATTERY_TIRE_INTERACTION"),
            ("rescue_cap_base", "PS_RESCUE_CAP_BASE"),
        ):
            value = slot_value(slot)
            if value is not None and str(value) != "UNRESOLVED":
                config[key] = value

        coverage: dict[str, Any] = {}
        if str(slot_value("PS_NOTICE_TIMELINESS") or "").lower() == "true":
            coverage["late_notice_issue"] = True
        if str(slot_value("PS_SUBROGATION_IMPAIRED") or "").lower() == "true":
            coverage["subrogation_impaired"] = True

        evidence = {
            item["node_id"]: item["node_id"] in self.evidence_present()
            for item in self.kb.evidence.values()
        }

        payload: dict[str, Any] = {
            "claim_id": self.claim_id,
            "unit": self.unit,
            "regulatory_snapshot": {"iranian_year": slot_value("PS_CLAIM_YEAR") or 1405},
            "classification": {},
            "vehicle": vehicle,
            "event": event,
            "damage": damage,
            "policy": {
                "endorsements": endorsements,
                **({"franchise": franchise} if isinstance(franchise, dict) else {}),
            },
            "evidence": evidence,
            "coverage_gate": coverage,
            "calculation_config": config,
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

    def decision(self) -> dict[str, Any]:
        """What the pipeline may issue now. This is the only gate that answers it."""
        classification = self.classification()
        branch = classification.get("branch")
        hard_open = [item for item in self.blocking_unanswered()]
        refused_by = self.refusal_reasons()

        if refused_by:
            kind = DECISION_REFUSE
        elif branch is None:
            kind = DECISION_INSUFFICIENT
        elif self.has_hard_blockers(hard_open):
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
            "live_uncertainties": self.open_uncertainties(),
            "missing_evidence": [entry["item"] for entry in self.missing_evidence()],
        }

    def has_hard_blockers(self, hard_open: list[str] | None = None) -> bool:
        hard_open = hard_open if hard_open is not None else self.blocking_unanswered()
        return any(
            (self.kb.question(item) or {}).get("blocking") == "hard"
            for item in hard_open
        )

    def refusal_reasons(self) -> list[str]:
        """Coverage-gate answers that stop the file before arithmetic."""
        reasons: list[str] = []
        if str(self.answer("Q-S0-06") or "").upper() in ("LAPSED", "INSTALMENT_OVERDUE"):
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

    def calculate(self) -> CalcResult | None:
        kind = self.decision()["decision"]
        if kind in (DECISION_REFUSE, DECISION_INSUFFICIENT):
            return None
        return compute(self.case_payload(), self.kb)

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
                add(f"  payable: {money.fmt(result.payable, self.unit)}")
            for index, value in enumerate(result.payable_scenarios):
                add(f"  scenario {chr(ord('A') + index)}: {money.fmt(value, self.unit)}")
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
    """The review-and-calculation flowchart, drawn from the graph itself."""
    lines = ["```mermaid", "flowchart TD"]
    lines.append(f"  START {_q('Claim file opened')} --> S0 {_q('0. Establish the file: dates, insurer, driver, cover in force')}")
    previous = "S0"
    for stage in kb.ordered_stages():
        node_id = stage["node_id"].split("_", 1)[0]
        if node_id == "S0":
            continue
        label = "%s. %s" % (stage["order"], stage["name"])
        lines.append("  %s --> %s %s" % (previous, node_id, _q(label)))
        previous = node_id

    lines.append('  %s --> GATE {"Decision gate: what may be issued?"}' % previous)
    lines.append(f"  GATE -- refusal established --> REFUSE {_q('REFUSE: denial with the provision named')}")
    lines.append(f"  GATE -- a hard question still open --> INSUF {_q('INSUFFICIENT_INFORMATION: the open question is printed, no amount')}")
    lines.append("  GATE -- classified --> BRANCH{Branch}")
    for branch in sorted(kb.branches):
        info = kb.branch(branch) or {}
        if info.get("domain") != "BODY":
            continue
        operators = len(info.get("operators") or [])
        label = "%s: %s operators, order %s" % (
            info.get("label_fa", ""),
            operators,
            info.get("order_status"),
        )
        lines.append("  BRANCH -- %s --> E_%s %s" % (branch, branch, _q(label)))
        lines.append(f"  E_{branch} --> PAY_{branch} {_q('SINGLE_PAYABLE: trace + provenance + confidence')}")
        lines.append(f"  E_{branch} --> SCEN_{branch} {_q('SCENARIO_SET: one outcome per sourced operator order')}")
        lines.append(f"  E_{branch} --> STOP_{branch} {_q('REFUSE: names the document or term that is missing')}")
        lines.append(f"  SCEN_{branch} --> ESC {_q('ESCALATE: insurer, assessor or underwriting')}")
        lines.append(f"  STOP_{branch} --> ESC")
        lines.append(f"  PAY_{branch} --> TRACE {_q('Audit trace: rules, operators, provenance, confidence')}")
    lines.append("  REFUSE --> ESC")
    lines.append("  INSUF --> ESC")
    lines.append("  ESC --> TRACE")
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
