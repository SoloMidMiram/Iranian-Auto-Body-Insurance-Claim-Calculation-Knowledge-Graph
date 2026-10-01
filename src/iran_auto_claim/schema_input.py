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
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from .knowledge import DEFAULT_ROOT

CLAIM_SCHEMA = "claim-case.schema.json"
REVIEW_SCHEMA = "review-answers.schema.json"

CODE_MISSING = "missing_field"
CODE_UNKNOWN = "unknown_field"
CODE_TYPE = "invalid_type"
CODE_ENUM = "invalid_enum"
CODE_BOOLEAN = "invalid_boolean"


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


def validate_review(payload: Any) -> None:
    _require(payload, _load(REVIEW_SCHEMA))


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
    return any(instance == item for item in allowed)


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
    if isinstance(instance, str):
        try:
            return Decimal(instance).is_finite()
        except InvalidOperation:
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
