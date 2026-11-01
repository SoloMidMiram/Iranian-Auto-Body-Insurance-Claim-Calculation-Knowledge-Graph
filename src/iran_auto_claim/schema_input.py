"""Runtime enforcement of the two claim input schemas.

``schema/claim-case.schema.json`` is the calculation case.
``schema/review-answers.schema.json`` is the questionnaire file.
``calc``, ``json``, ``classify``, ``review``, and ``compute`` all call this module.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from .dates import CalendarDateError, ClaimDate, parse_claim_date
from .knowledge import DEFAULT_ROOT

CLAIM_SCHEMA = "claim-case.schema.json"
REVIEW_SCHEMA = "review-answers.schema.json"

CODE_MISSING = "missing_field"
CODE_UNKNOWN = "unknown_field"
CODE_TYPE = "invalid_type"
CODE_ENUM = "invalid_enum"
CODE_BOOLEAN = "invalid_boolean"
CODE_UNAUTHORIZED = "review_not_authorized"
CODE_SCHEMA = "unsupported_schema_keyword"
CODE_JSON = "invalid_json"
CODE_DATE = "invalid_date"
CODE_CHRONOLOGY = "invalid_chronology"
CODE_CONFLICT = "conflicting_alias"
CODE_CONTRADICTION = "contradictory_input"
CODE_YEAR = "conflicting_year"
CODE_INVALID_YEAR = "invalid_year"

_SUPPORTED_SCHEMA_KEYS = {
    "$schema", "$id", "title", "description", "default",
    "type", "const", "enum", "minimum", "maximum", "minLength", "minProperties",
    "pattern", "format", "uniqueItems", "required", "properties", "patternProperties",
    "propertyNames", "additionalProperties", "items", "allOf", "anyOf", "if", "then", "else",
    "x-answer-formats", "x-refusals",
}


@dataclass(frozen=True)
class SchemaIssue:
    code: str
    path: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "path": self.path, "message": self.message}


class InputSchemaError(ValueError):
    """A claim or review file failed its JSON Schema."""

    def __init__(self, errors: list[SchemaIssue]) -> None:
        self.errors = errors
        summary = "; ".join(f"{item.code} at {item.path}" for item in errors)
        super().__init__(summary or "input schema rejected the document")


def validate_claim(payload: Any) -> None:
    _require(payload, _load(CLAIM_SCHEMA))
    issues = _claim_issues(payload)
    if issues:
        raise InputSchemaError(issues)


def validate_review(payload: Any, kb: Any | None = None) -> None:
    _require(payload, _load(REVIEW_SCHEMA))
    if kb is None:
        from .knowledge import Knowledge

        kb = Knowledge.load()
    issues = _review_issues(payload, kb)
    if issues:
        raise InputSchemaError(issues)


def validated_case(payload: Any) -> Any:
    """Return a Case only after its raw payload passes the shared boundary."""
    from .case import Case

    raw = payload.raw if isinstance(payload, Case) else payload
    validate_claim(raw)
    return payload if isinstance(payload, Case) else Case(raw)


def write_validated_claim(path: Path | str, payload: Any) -> None:
    """Validate and write JSON without turning Decimal amounts into strings or floats."""
    validate_claim(payload)
    Path(path).write_text(_encode_json(payload, 0) + "\n", encoding="utf-8")


def load_json_document(path: Path | str) -> Any:
    """Load a JSON document and expose parse failures through the stable error model."""
    target = Path(path)
    try:
        return json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise InputSchemaError(
            [SchemaIssue(CODE_JSON, "$", f"invalid JSON at line {error.lineno}, column {error.colno}")]
        ) from error


def _require(payload: Any, schema: dict[str, Any]) -> None:
    issues: list[SchemaIssue] = []
    _check(payload, schema, "", issues)
    if issues:
        raise InputSchemaError(issues)


def _load(name: str) -> dict[str, Any]:
    path = Path(DEFAULT_ROOT) / "schema" / name
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise InputSchemaError(
            [SchemaIssue(CODE_TYPE, name, "schema document must be an object")]
        )
    unsupported: list[SchemaIssue] = []
    _check_schema_keywords(loaded, "$", unsupported)
    if unsupported:
        raise InputSchemaError(unsupported)
    return loaded


def _check(instance: Any, schema: dict[str, Any], path: str, issues: list[SchemaIssue]) -> None:
    if "allOf" in schema:
        for child in schema["allOf"]:
            if isinstance(child, dict):
                _check(instance, child, path, issues)
    if "anyOf" in schema:
        _check_any(instance, schema["anyOf"], path, issues)
    if "if" in schema and isinstance(schema["if"], dict):
        trial: list[SchemaIssue] = []
        _check(instance, schema["if"], path, trial)
        follow = schema.get("then") if not trial else schema.get("else")
        if isinstance(follow, dict):
            _check(instance, follow, path, issues)

    if "const" in schema and instance != schema["const"]:
        issues.append(SchemaIssue(CODE_ENUM, path or "$", f"value must be {schema['const']!r}"))
        return
    if "enum" in schema and not _enum_holds(instance, schema["enum"]):
        issues.append(
            SchemaIssue(CODE_ENUM, path or "$", "value is outside the closed set")
        )
        return

    expected = schema.get("type")
    if expected is not None and not _type_holds(instance, expected):
        code = CODE_BOOLEAN if _boolean_mismatch(instance, expected) else CODE_TYPE
        issues.append(SchemaIssue(code, path or "$", _type_message(instance, expected)))
        return

    if isinstance(instance, dict):
        _check_object(instance, schema, path, issues)
    elif isinstance(instance, list) and "items" in schema and isinstance(schema["items"], dict):
        for index, item in enumerate(instance):
            _check(item, schema["items"], f"{path}[{index}]", issues)
        if schema.get("uniqueItems") and len(instance) != len(_freeze(instance)):
            issues.append(SchemaIssue(CODE_TYPE, path or "$", "items must be unique"))

    if isinstance(instance, str):
        pattern = schema.get("pattern")
        if pattern and re.fullmatch(pattern, instance) is None:
            issues.append(SchemaIssue(CODE_TYPE, path or "$", "value does not match the required pattern"))
        minimum = schema.get("minLength")
        if isinstance(minimum, int) and len(instance) < minimum:
            issues.append(SchemaIssue(CODE_TYPE, path or "$", "value is empty"))
        if schema.get("format") == "date":
            try:
                date.fromisoformat(instance)
            except ValueError:
                issues.append(SchemaIssue(CODE_TYPE, path or "$", "value must be an ISO date"))
    if _is_number(instance):
        _check_bounds(instance, schema, path, issues)


def _check_any(instance: Any, options: Any, path: str, issues: list[SchemaIssue]) -> None:
    if not isinstance(options, list) or not options:
        return
    groups: list[list[SchemaIssue]] = []
    for option in options:
        if not isinstance(option, dict):
            continue
        group: list[SchemaIssue] = []
        _check(instance, option, path, group)
        if not group:
            return
        groups.append(group)
    if groups:
        issues.extend(min(groups, key=len))


def _check_object(
    instance: dict[str, Any], schema: dict[str, Any], path: str, issues: list[SchemaIssue]
) -> None:
    properties = schema.get("properties") if isinstance(schema.get("properties"), dict) else {}
    patterns = schema.get("patternProperties") if isinstance(schema.get("patternProperties"), dict) else {}
    additional = schema.get("additionalProperties", True)
    name_pattern = ""
    property_names = schema.get("propertyNames")
    if isinstance(property_names, dict) and isinstance(property_names.get("pattern"), str):
        name_pattern = property_names["pattern"]

    for key in schema.get("required") or []:
        if key not in instance:
            issues.append(
                SchemaIssue(CODE_MISSING, _child(path, str(key)), "required field is missing")
            )

    minimum = schema.get("minProperties")
    if isinstance(minimum, int) and len(instance) < minimum:
        issues.append(SchemaIssue(CODE_MISSING, path or "$", "object has no entries"))

    for key, value in instance.items():
        child = _child(path, str(key))
        if name_pattern and re.fullmatch(name_pattern, str(key)) is None:
            issues.append(SchemaIssue(CODE_UNKNOWN, child, "field name is not in the closed set"))
            continue
        if key in properties and isinstance(properties[key], dict):
            _check(value, properties[key], child, issues)
            continue
        matched = False
        for pattern, subschema in patterns.items():
            if re.fullmatch(str(pattern), str(key)) and isinstance(subschema, dict):
                _check(value, subschema, child, issues)
                matched = True
                break
        if matched:
            continue
        if additional is False:
            issues.append(SchemaIssue(CODE_UNKNOWN, child, "field is not in the schema"))
        elif isinstance(additional, dict):
            _check(value, additional, child, issues)


def _check_bounds(instance: Any, schema: dict[str, Any], path: str, issues: list[SchemaIssue]) -> None:
    number = Decimal(str(instance))
    if isinstance(instance, float) and (math.isnan(instance) or math.isinf(instance)):
        issues.append(SchemaIssue(CODE_TYPE, path or "$", "number must be finite"))
        return
    minimum = schema.get("minimum")
    maximum = schema.get("maximum")
    if minimum is not None and number < Decimal(str(minimum)):
        issues.append(SchemaIssue(CODE_TYPE, path or "$", f"value is below {minimum}"))
    if maximum is not None and number > Decimal(str(maximum)):
        issues.append(SchemaIssue(CODE_TYPE, path or "$", f"value is above {maximum}"))


def _enum_holds(instance: Any, allowed: Any) -> bool:
    if not isinstance(allowed, list):
        return True
    return any(type(instance) is type(item) and instance == item for item in allowed)


def _type_holds(instance: Any, expected: Any) -> bool:
    options = expected if isinstance(expected, list) else [expected]
    return any(_one_type(instance, name) for name in options)


def _one_type(instance: Any, name: Any) -> bool:
    if name == "object":
        return isinstance(instance, dict)
    if name == "array":
        return isinstance(instance, list)
    if name == "string":
        return isinstance(instance, str)
    if name == "boolean":
        return isinstance(instance, bool)
    if name == "integer":
        return isinstance(instance, int) and not isinstance(instance, bool)
    if name == "number":
        return _is_number(instance)
    if name == "null":
        return instance is None
    return True


def _is_number(instance: Any) -> bool:
    if isinstance(instance, bool):
        return False
    if isinstance(instance, Decimal):
        return instance.is_finite()
    if isinstance(instance, float):
        return math.isfinite(instance)
    return isinstance(instance, int)


def _boolean_mismatch(instance: Any, expected: Any) -> bool:
    options = expected if isinstance(expected, list) else [expected]
    if isinstance(instance, bool) and "boolean" not in options:
        return True
    if "boolean" in options and not isinstance(instance, bool):
        return True
    return False


def _type_message(instance: Any, expected: Any) -> str:
    if _boolean_mismatch(instance, expected):
        return "value must be a JSON boolean"
    return f"value has the wrong type for {expected}"


def _child(path: str, key: str) -> str:
    return key if not path else f"{path}.{key}"


def _freeze(values: list[Any]) -> set[str]:
    frozen: set[str] = set()
    for item in values:
        frozen.add(json.dumps(item, sort_keys=True, default=str))
    return frozen


def _check_schema_keywords(
    schema: dict[str, Any], path: str, issues: list[SchemaIssue]
) -> None:
    for key in schema:
        if key not in _SUPPORTED_SCHEMA_KEYS:
            issues.append(
                SchemaIssue(
                    CODE_SCHEMA,
                    f"{path}.{key}",
                    "runtime validator does not implement this keyword",
                )
            )
    for container in ("properties", "patternProperties"):
        children = schema.get(container)
        if isinstance(children, dict):
            for name, child in children.items():
                if isinstance(child, dict):
                    _check_schema_keywords(child, f"{path}.{container}.{name}", issues)
    for key in ("additionalProperties", "items", "propertyNames", "if", "then", "else"):
        child = schema.get(key)
        if isinstance(child, dict):
            _check_schema_keywords(child, f"{path}.{key}", issues)
    for key in ("allOf", "anyOf"):
        children = schema.get(key)
        if isinstance(children, list):
            for index, child in enumerate(children):
                if isinstance(child, dict):
                    _check_schema_keywords(child, f"{path}.{key}[{index}]", issues)


_CLAIM_MONEY_ALIAS_GROUPS: tuple[tuple[str, ...], ...] = (
    ("damage.labor", "damage.labor_irr"),
    ("damage.gross", "damage.gross_damage", "damage.gross_damage_irr"),
    (
        "damage.repair",
        "damage.repair_total",
        "damage.repair_total_irr",
        "damage.repair_and_replacement_irr",
    ),
    ("damage.depreciation", "damage.assessed_depreciation_irr"),
    ("damage.depreciable_parts", "damage.depreciable_parts_base_irr"),
    (
        "damage.rescue",
        "damage.actual_rescue",
        "damage.rescue_transport_actual_irr",
    ),
    ("damage.rescue_for_threshold", "damage.rescue_for_total_loss_test_irr"),
    ("damage.market", "damage.market_value", "vehicle.market_value_at_event_irr"),
    ("damage.insured", "damage.insured_sum", "vehicle.insured_sum_irr"),
    ("damage.salvage", "damage.salvage_value", "vehicle.salvage_value_irr"),
    ("damage.actual_damage", "damage.actual_financial_loss_irr"),
    (
        "damage.corresponding_damage",
        "damage.similar_part_corresponding_damage",
        "damage.article8_corresponding_damage_irr",
    ),
    (
        "damage.policy_financial_limit",
        "damage.tp_limit",
        "policy.third_party_financial_limit_irr",
    ),
    ("damage.vehicle_value", "damage.victim_vehicle_value"),
    ("damage.conventional_threshold", "damage.threshold"),
)


def _claim_issues(payload: Any) -> list[SchemaIssue]:
    """Enforce cross-field contracts that JSON Schema cannot express."""
    if not isinstance(payload, dict):
        return []
    issues: list[SchemaIssue] = []

    parsed: dict[str, ClaimDate] = {}
    event = payload.get("event")
    if isinstance(event, dict):
        for field in ("event_date", "awareness_date", "declaration_date"):
            if event.get(field) not in (None, ""):
                parsed_date = _date_issue(
                    event[field],
                    f"event.{field}",
                    issues,
                    require_iranian_mapping=field == "event_date",
                )
                if parsed_date is not None:
                    parsed[field] = parsed_date
        clock = event.get("theft_clock")
        if isinstance(clock, dict):
            calendar = clock.get("calendar")
            start = _date_issue(
                clock.get("start_date"),
                "event.theft_clock.start_date",
                issues,
                calendar=calendar,
            )
            as_of = _date_issue(
                clock.get("as_of_date"),
                "event.theft_clock.as_of_date",
                issues,
                calendar=calendar,
            )
            if start is not None and as_of is not None and as_of.chronology_key < start.chronology_key:
                issues.append(
                    SchemaIssue(
                        CODE_CHRONOLOGY,
                        "event.theft_clock.as_of_date",
                        "theft-clock as-of date precedes its selected start date",
                    )
                )

    _check_event_chronology(parsed, "event", issues)

    snapshot = payload.get("regulatory_snapshot")
    snapshot = snapshot if isinstance(snapshot, dict) else {}
    claim_year = snapshot.get("iranian_year")
    event_date = parsed.get("event_date")
    if claim_year is not None and not 1 <= int(claim_year) < 3178:
        issues.append(
            SchemaIssue(
                CODE_INVALID_YEAR,
                "regulatory_snapshot.iranian_year",
                "Iranian claim year is outside the supported Shamsi interval",
            )
        )
    if event_date is not None and claim_year is not None and int(claim_year) != event_date.iranian_year:
        issues.append(
            SchemaIssue(
                CODE_YEAR,
                "regulatory_snapshot.iranian_year",
                f"Iranian claim year must equal event year {event_date.iranian_year}",
            )
        )

    vehicle = payload.get("vehicle")
    vehicle = vehicle if isinstance(vehicle, dict) else {}
    damage = payload.get("damage")
    damage = damage if isinstance(damage, dict) else {}
    production_values = [
        ("vehicle.production_year_shamsi", vehicle.get("production_year_shamsi")),
        ("damage.production_year", damage.get("production_year")),
    ]
    present_production = [(path, value) for path, value in production_values if value is not None]
    if len({value for _, value in present_production}) > 1:
        issues.append(
            SchemaIssue(
                CODE_CONFLICT,
                present_production[-1][0],
                "production-year representations describe the same Shamsi year and must agree",
            )
        )
    effective_year = event_date.iranian_year if event_date is not None else claim_year
    for path, production_year in present_production:
        if not 1 <= int(production_year) < 3178:
            issues.append(
                SchemaIssue(
                    CODE_INVALID_YEAR,
                    path,
                    "production year is outside the supported Shamsi interval",
                )
            )
        elif effective_year is not None and int(production_year) > int(effective_year):
            issues.append(
                SchemaIssue(
                    CODE_CHRONOLOGY,
                    path,
                    f"production year {production_year} is after event year {effective_year}",
                )
            )

    for group in _CLAIM_MONEY_ALIAS_GROUPS:
        _check_alias_group(payload, group, issues)
    for paths in (
        ("vehicle.salvage_disposition", "damage.salvage_disposition"),
        ("vehicle.title_transferred", "vehicle.title_transferred_to_insurer", "damage.title_transferred"),
    ):
        present = [(path, _path_value(payload, path)) for path in paths]
        present = [(path, value) for path, value in present if value is not None]
        if present and any(value != present[0][1] for _, value in present[1:]):
            issues.append(SchemaIssue(CODE_CONFLICT, present[-1][0],
                                      f"settlement evidence conflicts with {present[0][0]}"))
    if isinstance(damage.get("franchise"), (int, float)):
        policy_spec = (payload.get("policy") or {}).get("franchise")
        if isinstance(policy_spec, dict):
            issues.append(SchemaIssue(CODE_CONFLICT, "damage.franchise",
                                      "multiple franchise declarations require an explicit resolved contractual term"))
    actual_rescue = next(
        (
            damage.get(name)
            for name in (
                "rescue",
                "actual_rescue",
                "rescue_transport_actual_irr",
            )
            if damage.get(name) is not None
        ),
        None,
    )
    threshold_rescue = next(
        (
            damage.get(name)
            for name in (
                "rescue_for_threshold",
                "rescue_for_total_loss_test_irr",
            )
            if damage.get(name) is not None
        ),
        None,
    )
    rescue_source = damage.get("rescue_for_total_loss_test_source")
    if rescue_source == "DERIVED_FROM_ACTUAL_RESCUE":
        if actual_rescue is None:
            issues.append(
                SchemaIssue(
                    CODE_CONTRADICTION,
                    "damage.rescue_for_total_loss_test_source",
                    "DERIVED_FROM_ACTUAL_RESCUE requires an actual-rescue operand",
                )
            )
        elif threshold_rescue is not None and threshold_rescue != actual_rescue:
            issues.append(
                SchemaIssue(
                    CODE_CONTRADICTION,
                    "damage.rescue_for_total_loss_test_source",
                    "DERIVED_FROM_ACTUAL_RESCUE requires the classification "
                    "operand to match actual rescue",
                )
            )
    elif rescue_source == "EXPLICIT_THRESHOLD_OPERAND" and threshold_rescue is None:
        issues.append(
            SchemaIssue(
                CODE_CONTRADICTION,
                "damage.rescue_for_total_loss_test_source",
                "EXPLICIT_THRESHOLD_OPERAND requires a classification-rescue operand",
            )
        )
    for index, part in enumerate(damage.get("parts") or []):
        if isinstance(part, dict):
            _check_local_aliases(
                part,
                ("assessed_loss", "assessed_loss_irr"),
                f"damage.parts[{index}]",
                issues,
            )
            if part.get("category") == "REPAIR_ONLY" and part.get("requires_replacement") is True:
                issues.append(
                    SchemaIssue(
                        CODE_CONTRADICTION,
                        f"damage.parts[{index}].requires_replacement",
                        "REPAIR_ONLY work cannot be marked as requiring replacement",
                    )
                )
    for index, part in enumerate(damage.get("replacement_parts") or []):
        if isinstance(part, dict):
            _check_local_aliases(
                part,
                ("loss", "assessed_loss"),
                f"damage.replacement_parts[{index}]",
                issues,
            )
            repair_only_field = (
                "type" if part.get("type") == "REPAIR_ONLY" else "category"
            )
            if part.get(repair_only_field) == "REPAIR_ONLY":
                issues.append(
                    SchemaIssue(
                        CODE_CONTRADICTION,
                        f"damage.replacement_parts[{index}].{repair_only_field}",
                        "replacement_parts cannot contain REPAIR_ONLY work",
                    )
                )
    return issues


def _date_issue(
    value: Any,
    path: str,
    issues: list[SchemaIssue],
    *,
    calendar: Any = None,
    require_iranian_mapping: bool = False,
) -> ClaimDate | None:
    try:
        parsed = parse_claim_date(
            value, calendar=None if calendar is None else str(calendar)
        )
        if require_iranian_mapping:
            parsed.iranian_year
        return parsed
    except CalendarDateError as error:
        issues.append(SchemaIssue(CODE_DATE, path, str(error)))
        return None


def _check_event_chronology(
    parsed: dict[str, ClaimDate], prefix: str, issues: list[SchemaIssue],
    paths: dict[str, str] | None = None,
) -> None:
    def field_path(field: str) -> str:
        return (paths or {}).get(field, f"{prefix}.{field}")

    event = parsed.get("event_date")
    awareness = parsed.get("awareness_date")
    declaration = parsed.get("declaration_date")
    if event is not None and awareness is not None and awareness.chronology_key < event.chronology_key:
        issues.append(
            SchemaIssue(
                CODE_CHRONOLOGY,
                field_path("awareness_date"),
                "awareness date precedes the loss event",
            )
        )
    if event is not None and declaration is not None and declaration.chronology_key < event.chronology_key:
        issues.append(
            SchemaIssue(
                CODE_CHRONOLOGY,
                field_path("declaration_date"),
                "declaration date precedes the loss event",
            )
        )
    if awareness is not None and declaration is not None and declaration.chronology_key < awareness.chronology_key:
        issues.append(
            SchemaIssue(
                CODE_CHRONOLOGY,
                field_path("declaration_date"),
                "declaration date precedes awareness of the loss",
            )
        )


def _path_value(payload: dict[str, Any], path: str) -> Any:
    current: Any = payload
    for field in path.split("."):
        if not isinstance(current, dict) or field not in current:
            return None
        current = current[field]
    return current


def _check_alias_group(
    payload: dict[str, Any], paths: tuple[str, ...], issues: list[SchemaIssue]
) -> None:
    present = [(path, _path_value(payload, path)) for path in paths]
    present = [(path, value) for path, value in present if value is not None]
    valid = [(path, value) for path, value in present if _review_number(value)]
    if len(valid) > 1 and any(value != valid[0][1] for _, value in valid[1:]):
        issues.append(
            SchemaIssue(
                CODE_CONFLICT,
                valid[-1][0],
                f"monetary aliases must agree with {valid[0][0]}",
            )
        )


def _check_local_aliases(
    item: dict[str, Any], keys: tuple[str, ...], path: str, issues: list[SchemaIssue]
) -> None:
    present = [(key, item[key]) for key in keys if item.get(key) is not None]
    valid = [(key, value) for key, value in present if _review_number(value)]
    if len(valid) > 1 and any(value != valid[0][1] for _, value in valid[1:]):
        issues.append(
            SchemaIssue(
                CODE_CONFLICT,
                f"{path}.{valid[-1][0]}",
                f"monetary aliases must agree with {path}.{valid[0][0]}",
            )
        )


def _review_issues(payload: Any, kb: Any) -> list[SchemaIssue]:
    """Apply the graph's closed question/evidence vocabularies at the same boundary."""
    if not isinstance(payload, dict):
        return []
    issues: list[SchemaIssue] = []
    answers = payload.get("answers")
    if isinstance(answers, dict):
        for question_id, value in answers.items():
            path = f"answers.{question_id}"
            question = kb.question(question_id)
            if question is None:
                issues.append(SchemaIssue(CODE_UNKNOWN, path, "question is not in the procedure"))
                continue
            fmt = question.get("answer_format")
            allowed = question.get("answers") or []
            if fmt == "choice":
                if not isinstance(value, str) or value not in allowed:
                    issues.append(SchemaIssue(CODE_ENUM, path, "answer is outside the closed set"))
            elif fmt == "money" and not _review_number(value):
                issues.append(SchemaIssue(CODE_TYPE, path, "answer must be a finite number"))
            elif fmt == "integer" and not (
                isinstance(value, int) and not isinstance(value, bool)
            ):
                issues.append(SchemaIssue(CODE_TYPE, path, "answer must be an integer"))
            elif fmt == "date":
                calendar = None
                if question_id in ("Q-S2-11", "Q-S2-12"):
                    calendar = answers.get("Q-S2-13")
                _date_issue(
                    value,
                    path,
                    issues,
                    calendar=calendar,
                    require_iranian_mapping=question_id == "Q-S0-02",
                )
            elif fmt == "list":
                _check_review_list(question_id, value, allowed, path, issues)

        review_dates: dict[str, ClaimDate] = {}
        for field, question_id in (
            ("event_date", "Q-S0-02"),
            ("awareness_date", "Q-S0-03"),
            ("declaration_date", "Q-S0-07"),
        ):
            if answers.get(question_id) not in (None, ""):
                try:
                    parsed_date = parse_claim_date(answers[question_id])
                    if field == "event_date":
                        parsed_date.iranian_year
                    review_dates[field] = parsed_date
                except CalendarDateError:
                    pass
        _check_event_chronology(
            review_dates,
            "answers",
            issues,
            paths={
                "event_date": "answers.Q-S0-02",
                "awareness_date": "answers.Q-S0-03",
                "declaration_date": "answers.Q-S0-07",
            },
        )
        event_date = review_dates.get("event_date")
        production_year = answers.get("Q-S5-03")
        if isinstance(production_year, int) and not isinstance(production_year, bool):
            if not 1 <= production_year < 3178:
                issues.append(
                    SchemaIssue(
                        CODE_INVALID_YEAR,
                        "answers.Q-S5-03",
                        "production year is outside the supported Shamsi interval",
                    )
                )
            elif event_date is not None and production_year > event_date.iranian_year:
                issues.append(
                    SchemaIssue(
                        CODE_CHRONOLOGY,
                        "answers.Q-S5-03",
                        f"production year {production_year} is after event year {event_date.iranian_year}",
                    )
                )

    if payload.get("as_of") not in (None, ""):
        _date_issue(payload["as_of"], "as_of", issues)

    known_evidence = set(kb.evidence)
    for field in ("evidence_present", "evidence_received"):
        values = payload.get(field)
        if not isinstance(values, list):
            continue
        for index, value in enumerate(values):
            if value not in known_evidence:
                issues.append(
                    SchemaIssue(CODE_ENUM, f"{field}[{index}]", "evidence id is outside the closed set")
                )
    return issues


def _check_review_list(
    question_id: str,
    value: Any,
    allowed: list[Any],
    path: str,
    issues: list[SchemaIssue],
) -> None:
    values = value if isinstance(value, list) else [value]
    if question_id != "Q-S4-03":
        for index, item in enumerate(values):
            if not isinstance(item, str) or item not in allowed:
                issues.append(
                    SchemaIssue(CODE_ENUM, f"{path}[{index}]", "answer is outside the closed set")
                )
        return

    permitted = {
        "name",
        "category",
        "assessed_loss",
        "assessed_loss_irr",
        "new_price",
        "new_price_irr",
        "requires_replacement",
    }
    for index, item in enumerate(values):
        item_path = f"{path}[{index}]"
        if not isinstance(item, dict):
            issues.append(SchemaIssue(CODE_TYPE, item_path, "part must be an object"))
            continue
        for key in item:
            if key not in permitted:
                issues.append(
                    SchemaIssue(
                        CODE_UNKNOWN,
                        f"{item_path}.{key}",
                        "field is not in the part schema",
                    )
                )
        category = item.get("category")
        if not isinstance(category, str) or category not in allowed:
            issues.append(
                SchemaIssue(
                    CODE_ENUM,
                    f"{item_path}.category",
                    "category is outside the closed set",
                )
            )
        if "assessed_loss" not in item and "assessed_loss_irr" not in item:
            issues.append(
                SchemaIssue(
                    CODE_MISSING,
                    f"{item_path}.assessed_loss",
                    "required field is missing",
                )
            )
        for key in ("assessed_loss", "assessed_loss_irr", "new_price", "new_price_irr"):
            if key in item and item[key] is not None and not _review_number(item[key]):
                issues.append(
                    SchemaIssue(
                        CODE_TYPE,
                        f"{item_path}.{key}",
                        "value must be a finite number",
                    )
                )
        _check_local_aliases(
            item,
            ("assessed_loss", "assessed_loss_irr"),
            item_path,
            issues,
        )
        _check_local_aliases(
            item,
            ("new_price", "new_price_irr"),
            item_path,
            issues,
        )
        if "requires_replacement" in item and not isinstance(item["requires_replacement"], bool):
            issues.append(
                SchemaIssue(
                    CODE_BOOLEAN,
                    f"{item_path}.requires_replacement",
                    "value must be a JSON boolean",
                )
            )
        if category == "REPAIR_ONLY" and item.get("requires_replacement") is True:
            issues.append(
                SchemaIssue(
                    CODE_CONTRADICTION,
                    f"{item_path}.requires_replacement",
                    "REPAIR_ONLY work cannot be marked as requiring replacement",
                )
            )


def _review_number(value: Any) -> bool:
    """Money answers cross the review boundary as non-negative integer IRR."""
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _encode_json(value: Any, level: int) -> str:
    """Small exact JSON encoder used for schema-shaped review exports."""
    pad = "  " * level
    child_pad = "  " * (level + 1)
    if isinstance(value, dict):
        if not value:
            return "{}"
        rows = [
            f"{child_pad}{json.dumps(str(key), ensure_ascii=False)}: {_encode_json(item, level + 1)}"
            for key, item in value.items()
        ]
        return "{\n" + ",\n".join(rows) + f"\n{pad}}}"
    if isinstance(value, (list, tuple)):
        if not value:
            return "[]"
        rows = [f"{child_pad}{_encode_json(item, level + 1)}" for item in value]
        return "[\n" + ",\n".join(rows) + f"\n{pad}]"
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("non-finite Decimal cannot be written as JSON")
        return format(value, "f")
    return json.dumps(value, ensure_ascii=False, allow_nan=False)
