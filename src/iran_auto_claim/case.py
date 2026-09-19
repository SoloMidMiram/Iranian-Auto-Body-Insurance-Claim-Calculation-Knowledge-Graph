"""Case parsing and input normalisation.

The engine's input contract is schema/claim-case.schema.json. This module is the
runtime half of that contract: it flattens the nested case into the lookups the
operators need, understands the documented scalar shorthands that assessment
estimators emit, and refuses ambiguous money.

Two rules matter for reviewer trust:

* A shortcut input is accepted only where the schema documents it, and it
  normalises into the same Part record a fully itemised case produces.
* Supplying only one of insured sum / market value is an error, not a silent
  ratio of 1. Underinsurance is either assessed from both figures or not
  assessed at all.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from .money import D

PART_CATEGORIES = (
    "GLASS",
    "LAMP_GLASS",
    "BATTERY",
    "TIRE",
    "OTHER_REPLACEMENT_PART",
    "REPAIR_ONLY",
)

BRANCH_ALIASES = {
    "TOTAL_LOSS_TEST": {"branch": "TOTAL_LOSS", "variant": "THRESHOLD_TEST"},
    "TOTAL_THEFT": {"branch": "THEFT", "variant": "TOTAL_SETTLEMENT"},
    "ARTICLE_8_DUAL_COVERAGE": {
        "branch": "ARTICLE_8_NON_CONVENTIONAL",
        "variant": "DUAL_COVERAGE",
    },
    "ORDINARY_FINANCIAL": {"branch": "THIRD_PARTY_FINANCIAL", "variant": "ORDINARY_FINANCIAL"},
    "THEFT_PARTIAL_DAMAGE": {"branch": "THEFT", "variant": "ATTEMPTED_THEFT"},
}

DOMAIN_BY_BRANCH = {
    "PARTIAL_DAMAGE": "BODY",
    "TOTAL_LOSS": "BODY",
    "GLASS_ONLY": "BODY",
    "THEFT": "BODY",
    "THIRD_PARTY_FINANCIAL": "THIRD_PARTY_FINANCIAL",
    "ARTICLE_8_NON_CONVENTIONAL": "THIRD_PARTY_FINANCIAL",
    "LEGAL_RECOVERY": "LEGAL_RECOVERY",
}

BASE_BODY_PERIL_KEYWORDS = (
    "COLLISION",
    "ACCIDENT",
    "FIRE",
    "OVERTURN",
    "ROLLOVER",
    "IMPACT",
    "CRASH",
)


class CaseInputError(ValueError):
    pass


def _num(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def _category(value: Any) -> str:
    """Part category is a closed vocabulary: a typo must fail loudly.

    An unrecognised category would silently take the no-cap, depreciating path,
    which is the wrong answer for a mis-spelled BATTERY or GLASS.
    """
    category = str(value).upper()
    if category not in PART_CATEGORIES:
        raise CaseInputError(
            f"unknown part category {value!r}; expected one of {', '.join(PART_CATEGORIES)}"
        )
    return category


class Case:
    def __init__(self, raw: dict[str, Any]) -> None:
        if not isinstance(raw, dict):
            raise CaseInputError("a case must be a JSON object")
        self.raw = raw
        self.claim_id = str(raw.get("claim_id") or raw.get("id") or "unnamed")
        self.unit = raw.get("unit") or "million_toman"

        self.damage = dict(raw.get("damage") or raw.get("inputs") or {})
        self.vehicle = dict(raw.get("vehicle") or {})
        self.event = dict(raw.get("event") or {})
        self.policy = dict(raw.get("policy") or {})
        self.config = dict(raw.get("calculation_config") or {})
        self.snapshot = dict(raw.get("regulatory_snapshot") or {})
        self.evidence = dict(raw.get("evidence") or {})
        self.coverage = dict(raw.get("coverage_gate") or {})

        classification = dict(raw.get("classification") or {})
        declared = classification.get("branch") or raw.get("branch")
        declared = str(declared) if declared else None
        alias = BRANCH_ALIASES.get(declared) if declared else None
        self.declared_branch = declared
        self.branch = alias["branch"] if alias else declared
        self.variant = (
            alias["variant"] if alias else classification.get("variant") or raw.get("variant")
        )
        self.domain = classification.get("domain") or DOMAIN_BY_BRANCH.get(self.branch)

    # ---------------------------------------------------------------- lookups

    def _find(self, keys: tuple[str, ...]) -> Any:
        for source in (self.damage, self.vehicle, self.event, self.policy, self.raw):
            for key in keys:
                if key in source and source[key] is not None:
                    return source[key]
        return None

    def _money(self, keys: tuple[str, ...]) -> Decimal | None:
        value = self._find(keys)
        return None if value is None else D(value)

    # ------------------------------------------------------------ core money

    @property
    def market_value(self) -> Decimal | None:
        return self._money(
            ("market", "market_value", "market_value_at_event", "market_value_at_event_irr")
        )

    @property
    def insured_sum(self) -> Decimal | None:
        return self._money(("insured", "insured_sum", "insured_sum_irr"))

    @property
    def production_year(self) -> int | None:
        return _num(self._find(("production_year", "production_year_shamsi")))

    @property
    def claim_year(self) -> int:
        return _num(self.snapshot.get("iranian_year")) or 1405

    @property
    def labor(self) -> Decimal | None:
        return self._money(("labor", "labor_irr"))

    @property
    def gross_damage(self) -> Decimal | None:
        return self._money(("gross", "gross_damage", "gross_damage_irr"))

    @property
    def repair_total(self) -> Decimal | None:
        return self._money(
            ("repair", "repair_total", "repair_total_irr", "repair_and_replacement", "repair_and_replacement_irr")
        )

    @property
    def assessed_depreciation(self) -> Decimal | None:
        return self._money(
            ("depreciation", "depreciation_irr", "assessed_depreciation", "assessed_depreciation_irr")
        )

    @property
    def depreciable_parts(self) -> Decimal | None:
        return self._money(("depreciable_parts", "depreciable_parts_base_irr"))

    @property
    def depreciation_rate(self) -> Decimal | None:
        value = self._find(("depreciation_rate",))
        return None if value is None else D(value)

    @property
    def rescue_actual(self) -> Decimal | None:
        return self._money(
            (
                "rescue_transport_actual",
                "rescue_transport_actual_irr",
                "actual_rescue",
                "rescue_payable",
                "rescue",
            )
        )

    @property
    def rescue_for_threshold(self) -> Decimal:
        return self._money(("rescue_for_threshold", "rescue_for_total_loss_test_irr")) or Decimal(0)

    @property
    def salvage(self) -> Decimal | None:
        return self._money(("salvage", "salvage_value", "salvage_value_irr"))

    @property
    def salvage_disposition(self) -> str:
        given = self._find(("salvage_disposition",))
        if given:
            return str(given)
        return "INSURED_RETAINS" if self.salvage is not None else "NOT_APPLICABLE"

    @property
    def title_transferred(self) -> bool:
        value = self._find(("title_transferred", "title_transferred_to_insurer"))
        return bool(value)

    @property
    def actual_damage(self) -> Decimal | None:
        return self._money(("actual_damage", "actual_financial_loss", "actual_financial_loss_irr"))

    @property
    def corresponding_damage(self) -> Decimal | None:
        return self._money(
            (
                "corresponding_damage",
                "similar_part_corresponding_damage",
                "article8_corresponding_damage",
                "article8_corresponding_damage_irr",
            )
        )

    @property
    def financial_limit(self) -> Decimal | None:
        return self._money(
            (
                "policy_financial_limit",
                "tp_limit",
                "third_party_financial_limit",
                "third_party_financial_limit_irr",
            )
        )

    @property
    def threshold(self) -> Decimal | None:
        return self._money(
            (
                "conventional_threshold",
                "conventional_vehicle_threshold",
                "conventional_vehicle_threshold_irr",
                "threshold",
            )
        )

    @property
    def victim_vehicle_value(self) -> Decimal | None:
        return self._money(("victim_vehicle_value", "vehicle_value")) or self.market_value

    # -------------------------------------------------------- event / policy

    @property
    def cause(self) -> str | None:
        value = self._find(("cause",))
        return None if value is None else str(value)

    @property
    def peril(self) -> str | None:
        value = self._find(("peril",))
        return None if value is None else str(value)

    @property
    def theft_type(self) -> str | None:
        value = self._find(("theft_type",))
        return None if value is None else str(value)

    @property
    def days_missing(self) -> int | None:
        return _num(self._find(("days_missing", "days_vehicle_missing")))

    @property
    def intoxication_causally_confirmed(self) -> bool:
        return bool(self._find(("intoxication_causally_confirmed",)))

    def field_value(self, name: str) -> Any:
        return self._find((name,))

    @property
    def property_type(self) -> str:
        value = self._find(("property_type", "damaged_property_type"))
        return str(value) if value else "PASSENGER_VEHICLE"

    @property
    def has_body_policy(self) -> bool | None:
        value = self._find(("has_body_policy",))
        return None if value is None else bool(value)

    @property
    def body_franchise_for_excess_disclosed(self) -> bool:
        return bool(self._find(("body_franchise_for_excess_disclosed",)))

    @property
    def body_insurer_paid(self) -> Decimal | None:
        return self._money(("body_insurer_paid",))

    @property
    def insured_released_responsible_party(self) -> bool:
        return bool(self._find(("insured_released_responsible_party",)))

    @property
    def recovery_right_impaired(self) -> bool:
        return bool(self._find(("recovery_right_impaired",)))

    @property
    def late_notice_issue(self) -> bool:
        return bool(self.coverage.get("late_notice_issue")) or bool(
            self._find(("late_notice_issue",))
        )

    @property
    def subrogation_impaired(self) -> bool:
        if self.coverage.get("subrogation_impaired"):
            return True
        return bool(self._find(("subrogation_impaired",)) or self.recovery_right_impaired)

    @property
    def franchise_raw(self) -> Any:
        return self._find(("franchise", "franchise_from_policy", "franchise_amount"))

    @property
    def policy_franchise(self) -> dict[str, Any] | None:
        value = self.policy.get("franchise")
        return dict(value) if isinstance(value, dict) else None

    def endorsement_tokens(self) -> set[str]:
        tokens: set[str] = set()
        listed = self.policy.get("endorsements") or self.raw.get("endorsements") or []
        if isinstance(listed, str):
            listed = [listed]
        for item in listed:
            if isinstance(item, str):
                tokens.add(item.upper())
        if self._find(("endorsement",)) is True:
            tokens.add("*")
        if self.coverage.get("endorsement_restores_excluded_peril"):
            tokens.add("*")
        if self._find(("glass_endorsement", "glass_only_endorsement")) is True:
            tokens.add("GLASS_ONLY")
        if self._find(("partial_theft_endorsement",)) is True:
            tokens.add("PARTIAL_THEFT")
        return tokens

    def has_endorsement(self, accepted_tokens: list[str]) -> bool:
        tokens = self.endorsement_tokens()
        if "*" in tokens:
            return True
        return any(token.upper() in tokens for token in accepted_tokens)

    @property
    def has_glass_endorsement(self) -> bool:
        return self.has_endorsement(["GLASS_ONLY", "GLASS"])

    @property
    def glass_damage_from_base_peril(self) -> bool:
        haystack = " ".join(filter(None, [self.cause or "", self.peril or ""])).upper()
        return any(keyword in haystack for keyword in BASE_BODY_PERIL_KEYWORDS)

    # ------------------------------------------------------------ components

    @property
    def parts(self) -> list[dict[str, Any]]:
        parts: list[dict[str, Any]] = []

        itemised = self.damage.get("parts")
        if isinstance(itemised, list):
            for entry in itemised:
                if not isinstance(entry, dict):
                    continue
                loss = entry.get("assessed_loss", entry.get("assessed_loss_irr"))
                if loss is None:
                    loss = entry.get("loss", 0)
                new_price = entry.get("new_price", entry.get("new_price_irr"))
                parts.append(
                    {
                        "name": entry.get("name"),
                        "category": _category(entry.get("category", "OTHER_REPLACEMENT_PART")),
                        "assessed_loss": D(loss),
                        "new_price": None if new_price is None else D(new_price),
                        "requires_replacement": bool(entry.get("requires_replacement", True)),
                    }
                )

        shorthand_list = self.damage.get("replacement_parts")
        if isinstance(shorthand_list, list):
            for entry in shorthand_list:
                if not isinstance(entry, dict):
                    continue
                loss = entry.get("loss", entry.get("assessed_loss", 0))
                parts.append(
                    {
                        "name": entry.get("name"),
                        "category": _category(entry.get("type", entry.get("category", "OTHER_REPLACEMENT_PART"))),
                        "assessed_loss": D(loss),
                        "new_price": None,
                        "requires_replacement": True,
                    }
                )

        battery_loss = self._find(("battery_loss",))
        if battery_loss is not None:
            new_price = self._find(("battery_new_price",))
            parts.append(
                {
                    "name": "battery",
                    "category": "BATTERY",
                    "assessed_loss": D(battery_loss),
                    "new_price": None if new_price is None else D(new_price),
                    "requires_replacement": True,
                }
            )

        tire_loss = self._find(("tire_loss", "tires_loss"))
        if tire_loss is not None:
            new_price = self._find(("tires_new_price", "tire_new_price"))
            parts.append(
                {
                    "name": "tires",
                    "category": "TIRE",
                    "assessed_loss": D(tire_loss),
                    "new_price": None if new_price is None else D(new_price),
                    "requires_replacement": True,
                }
            )

        lamp_glass = self._find(("lamp_glass",))
        if lamp_glass is not None:
            parts.append(
                {
                    "name": "lamp glass",
                    "category": "LAMP_GLASS",
                    "assessed_loss": D(lamp_glass),
                    "new_price": None,
                    "requires_replacement": True,
                }
            )

        other = self._find(("other_replacement_part",))
        if other is not None:
            override = self._find(("other_part_depreciation_rate",))
            parts.append(
                {
                    "name": "other replacement part",
                    "category": "OTHER_REPLACEMENT_PART",
                    "assessed_loss": D(other),
                    "new_price": None,
                    "requires_replacement": True,
                    "depreciation_rate": None if override is None else D(override),
                }
            )

        return parts
