#!/usr/bin/env python3
"""Compare an inspection observation with a reviewed, versioned reference manifest.

The manifest contains typed reference assertions, never an input verdict.  A registered
known deviation may describe the bounded current observation, but it remains separate
from both the reference authority classification and the computed comparison verdict.
"""

from __future__ import annotations

import argparse
from collections import Counter
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import hashlib
import json
from pathlib import Path
import re
from typing import Any

try:
    from .inspection_provenance import (
        BASE_MODEL_PATHS,
        INTERNAL_PROBE_ORIGINS_RELATIVE,
        ProvenanceError,
        model_identity,
        model_scope,
    )
except ImportError:  # Direct script execution.
    from inspection_provenance import (
        BASE_MODEL_PATHS,
        INTERNAL_PROBE_ORIGINS_RELATIVE,
        ProvenanceError,
        model_identity,
        model_scope,
    )


ALLOWED_BASES = {
    "CONTROLLED_MATH",
    "ENGINEERING_INVARIANT",
    "PRIMARY_AUTHORITY",
    "CONTRACT_TERM",
    "DOMAIN_ASSUMPTION",
    "UNRESOLVED",
}
REQUIRED_EXPECTATION_KEYS = {
    "process",
    "review_decision",
    "classification",
    "authorization",
    "calculation",
    "blocking_uncertainties",
    "trace_assertions",
}
TRACE_ROOTS = {
    "fields",
    "rule_trace",
    "review_parameters",
    "open_hard_questions",
    "open_blocking_questions",
    "evidence_blocks",
    "blocking_conditions",
    "required_guards",
    "guards_executed",
    "labels",
    "reason",
    "review_error_codes",
    "review_stderr",
}
HEX_DIGEST = re.compile(r"[0-9a-f]{64}")
MODEL_PATHS = BASE_MODEL_PATHS
MILLION_TOMAN_IRR = Decimal(10_000_000)
PAYABLE_LINE = re.compile(r"^  PAYABLE:\s+(.+?)\s*$", re.MULTILINE)
SCENARIOS_LINE = re.compile(r"^  SCENARIOS:\s+(\d+) outcomes\s*$", re.MULTILINE)
SCENARIO_LINE = re.compile(r"^    scenario ([A-Z]):\s+(.+?)\s*$", re.MULTILINE)
MISSING = object()


class ManifestError(ValueError):
    """The reference manifest is not safe to execute as an oracle."""


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"), parse_float=Decimal)
    except (OSError, json.JSONDecodeError) as error:
        raise ManifestError(f"cannot read valid JSON from {path}: {error}") from error


def _validate_model_binding(
    observation: dict[str, Any], model_root: Path
) -> tuple[str, str, tuple[str, ...], str]:
    include_internal = "internal_test_direct" in observation
    scope = model_scope(include_internal)
    profile = "SUPPORTED_PLUS_INTERNAL" if include_internal else "SUPPORTED_ONLY"
    try:
        revision, tree = model_identity(model_root, scope)
    except ProvenanceError as error:
        raise ManifestError(str(error)) from error
    observed_revision = observation.get("revision")
    observed_tree = observation.get("tree")
    if observed_revision != revision:
        raise ManifestError(
            "observation revision mismatch: "
            f"expected model {revision}, observed {observed_revision!r}"
        )
    if observed_tree != tree:
        raise ManifestError(
            f"observation tree mismatch: expected model {tree}, observed {observed_tree!r}"
        )
    if observation.get("provenance_profile") != profile:
        raise ManifestError(
            "observation provenance_profile is missing or incompatible with its evidence"
        )
    if observation.get("model_scope") != list(scope):
        raise ManifestError(
            "observation model_scope is missing or differs from the comparator scope"
        )
    if observation.get("import_origin_relative") != "src/iran_auto_claim/__init__.py":
        raise ManifestError("observation import origin is not the selected model package")
    if include_internal and observation.get(
        "internal_probe_import_origins_relative"
    ) != INTERNAL_PROBE_ORIGINS_RELATIVE:
        raise ManifestError(
            "internal probe import origins are missing or differ from the required map"
        )
    return revision, tree, scope, profile


def _unique_rows(rows: Any, key: str, label: str) -> dict[str, dict[str, Any]]:
    if not isinstance(rows, list):
        raise ManifestError(f"{label} must be a list")
    identifiers = [row.get(key) for row in rows if isinstance(row, dict)]
    if len(identifiers) != len(rows) or not all(isinstance(item, str) for item in identifiers):
        raise ManifestError(f"every {label} entry must have a string {key}")
    duplicates = sorted(name for name, count in Counter(identifiers).items() if count > 1)
    if duplicates:
        raise ManifestError(f"duplicate {label} {key}: {duplicates}")
    return {row[key]: row for row in rows}


def _money(value: Any, location: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or isinstance(value, float):
        raise ManifestError(f"{location} must use exact integer/decimal IRR, not float/bool")
    if not isinstance(value, (int, str, Decimal)):
        raise ManifestError(f"{location} must be an integer-IRR value or null")
    try:
        amount = Decimal(value)
    except (InvalidOperation, ValueError) as error:
        raise ManifestError(f"{location} is not exact money: {value!r}") from error
    if not amount.is_finite() or amount != amount.to_integral_value():
        raise ManifestError(f"{location} is not an integer IRR amount: {value!r}")
    return int(amount)


def _million_toman(value: Any, location: str) -> str:
    amount = _money(value, location)
    if amount is None:
        raise ManifestError(f"{location} cannot be null when rendering money")
    display = (Decimal(amount) / MILLION_TOMAN_IRR).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    return f"{display:,.2f} m-toman"


def _standalone_calculation_evidence(
    row: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    process = row.get("process") if isinstance(row.get("process"), dict) else {}
    calc_exit = process.get("calc_exit", MISSING)
    applicable = calc_exit == 0
    evidence: dict[str, Any] = {
        "applicable": applicable,
        "display_unit": "million_toman" if applicable else None,
        "irr_per_display_unit": int(MILLION_TOMAN_IRR) if applicable else None,
        "expected_payable": None,
        "observed_payable": None,
        "expected_scenarios": [],
        "observed_scenarios": [],
    }
    if not applicable:
        return evidence, []

    failures: list[dict[str, Any]] = []
    if row.get("calculation_present") is not True:
        failures.append(
            _failure(
                "standalone_calculation.calculation_present",
                True,
                row.get("calculation_present", MISSING),
                "successful claim calc has no structured Review calculation",
            )
        )
    stdout = row.get("calc_stdout", MISSING)
    if not isinstance(stdout, str):
        failures.append(
            _failure(
                "standalone_calculation.stdout",
                "rendered claim calc text",
                stdout,
                "calc stdout missing",
            )
        )
        return evidence, failures

    payable = row.get("payable_irr", MISSING)
    scenarios = row.get("payable_scenarios_irr", MISSING)
    try:
        expected_payable = (
            None
            if payable is None
            else _million_toman(payable, "observed.payable_irr")
        )
        if scenarios is None:
            expected_scenarios: list[str] = []
        elif isinstance(scenarios, list):
            expected_scenarios = [
                _million_toman(value, f"observed.payable_scenarios_irr[{index}]")
                for index, value in enumerate(scenarios)
            ]
        else:
            raise ManifestError("observed.payable_scenarios_irr must be a list or null")
    except ManifestError as error:
        failures.append(
            _failure(
                "standalone_calculation.structured_money",
                "exact integer IRR",
                {"payable_irr": payable, "payable_scenarios_irr": scenarios},
                str(error),
            )
        )
        return evidence, failures

    payable_lines = PAYABLE_LINE.findall(stdout)
    scenario_headers = [int(value) for value in SCENARIOS_LINE.findall(stdout)]
    scenario_lines = SCENARIO_LINE.findall(stdout)
    observed_payable = payable_lines[0] if len(payable_lines) == 1 else None
    observed_scenarios = [value for _, value in scenario_lines]
    evidence.update(
        {
            "expected_payable": expected_payable,
            "observed_payable": observed_payable,
            "expected_scenarios": expected_scenarios,
            "observed_scenarios": observed_scenarios,
        }
    )
    if len(payable_lines) > 1:
        failures.append(
            _failure(
                "standalone_calculation.payable_line_count",
                1 if expected_payable is not None else 0,
                len(payable_lines),
                "duplicate rendered payable lines",
            )
        )
    if observed_payable != expected_payable:
        failures.append(
            _failure(
                "standalone_calculation.payable_rendered",
                expected_payable,
                observed_payable,
                "rendered amount or display unit differs from exact IRR conversion",
            )
        )
    expected_header = [len(expected_scenarios)] if expected_scenarios else []
    if scenario_headers != expected_header:
        failures.append(
            _failure(
                "standalone_calculation.scenario_count",
                expected_header,
                scenario_headers,
            )
        )
    expected_labels = [
        chr(ord("A") + index) for index in range(len(expected_scenarios))
    ]
    observed_labels = [label for label, _ in scenario_lines]
    if observed_labels != expected_labels:
        failures.append(
            _failure(
                "standalone_calculation.scenario_labels",
                expected_labels,
                observed_labels,
            )
        )
    if observed_scenarios != expected_scenarios:
        failures.append(
            _failure(
                "standalone_calculation.scenarios_rendered",
                expected_scenarios,
                observed_scenarios,
                "rendered scenario amount or display unit differs from exact IRR conversion",
            )
        )
    return evidence, failures


def _validate_expectation(expected: Any, location: str) -> None:
    if not isinstance(expected, dict):
        raise ManifestError(f"{location} must be an object")
    missing = REQUIRED_EXPECTATION_KEYS - set(expected)
    unexpected = set(expected) - REQUIRED_EXPECTATION_KEYS
    if missing or unexpected:
        raise ManifestError(
            f"{location} keys invalid: missing={sorted(missing)}, unexpected={sorted(unexpected)}"
        )
    process = expected["process"]
    if not isinstance(process, dict) or set(process) != {"review_exit", "calc_exit"}:
        raise ManifestError(f"{location}.process must contain review_exit and calc_exit")
    if not all(isinstance(value, int) and not isinstance(value, bool) for value in process.values()):
        raise ManifestError(f"{location}.process exits must be integers")
    for key in ("review_decision", "classification"):
        if expected[key] is not None and not isinstance(expected[key], str):
            raise ManifestError(f"{location}.{key} must be a string or null")
    authorization = expected["authorization"]
    required_authorization = {"granted", "issuer", "decision", "branch"}
    if not isinstance(authorization, dict) or set(authorization) != required_authorization:
        raise ManifestError(f"{location}.authorization must contain {sorted(required_authorization)}")
    if not isinstance(authorization["granted"], bool):
        raise ManifestError(f"{location}.authorization.granted must be boolean")
    for key in ("issuer", "decision", "branch"):
        if authorization[key] is not None and not isinstance(authorization[key], str):
            raise ManifestError(f"{location}.authorization.{key} must be string or null")
    calculation = expected["calculation"]
    required_calculation = {"present", "status", "payable_irr", "payable_scenarios_irr"}
    if not isinstance(calculation, dict) or set(calculation) != required_calculation:
        raise ManifestError(f"{location}.calculation must contain {sorted(required_calculation)}")
    if not isinstance(calculation["present"], bool):
        raise ManifestError(f"{location}.calculation.present must be boolean")
    if calculation["status"] is not None and not isinstance(calculation["status"], str):
        raise ManifestError(f"{location}.calculation.status must be string or null")
    _money(calculation["payable_irr"], f"{location}.calculation.payable_irr")
    scenarios = calculation["payable_scenarios_irr"]
    if scenarios is not None:
        if not isinstance(scenarios, list):
            raise ManifestError(f"{location}.calculation.payable_scenarios_irr must be list or null")
        for index, value in enumerate(scenarios):
            _money(value, f"{location}.calculation.payable_scenarios_irr[{index}]")
    blocking = expected["blocking_uncertainties"]
    if not isinstance(blocking, dict) or set(blocking) != {"review", "calculation"}:
        raise ManifestError(f"{location}.blocking_uncertainties requires review and calculation")
    for key, value in blocking.items():
        if value is not None and not isinstance(value, list):
            raise ManifestError(f"{location}.blocking_uncertainties.{key} must be list or null")
    assertions = expected["trace_assertions"]
    if not isinstance(assertions, list) or not assertions:
        raise ManifestError(f"{location}.trace_assertions must be a non-empty list")
    for index, assertion in enumerate(assertions):
        item_location = f"{location}.trace_assertions[{index}]"
        if not isinstance(assertion, dict):
            raise ManifestError(f"{item_location} must be an object")
        if set(assertion) != {"path", "operator", "value"}:
            raise ManifestError(f"{item_location} requires path, operator and value")
        path = assertion["path"]
        if not isinstance(path, str) or path.split(".", 1)[0] not in TRACE_ROOTS:
            raise ManifestError(f"{item_location}.path is not an allowed material trace path")
        if assertion["operator"] not in {"equals", "contains", "contains_all", "money_equals"}:
            raise ManifestError(f"{item_location}.operator is unsupported")
        if assertion["operator"] == "money_equals":
            _money(assertion["value"], f"{item_location}.value")


def load_manifest(path: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    manifest = _load_json(path)
    if not isinstance(manifest, dict) or manifest.get("schema_version") != "1.0":
        raise ManifestError("manifest schema_version must be '1.0'")
    cases = _unique_rows(manifest.get("cases"), "case_id", "manifest cases")
    if len(cases) != 47:
        raise ManifestError(f"manifest must contain 47 cases, found {len(cases)}")
    for case_id, case in cases.items():
        digest = case.get("input_sha256")
        if not isinstance(digest, str) or not HEX_DIGEST.fullmatch(digest):
            raise ManifestError(f"{case_id}.input_sha256 must be lowercase SHA-256")
        reference = case.get("reference")
        required_reference = {
            "basis",
            "authority_status",
            "source_ids",
            "rule_locators",
            "effective_or_applicability_dates",
            "unit",
            "operator_order",
            "derivation",
            "reviewer",
            "review_status",
        }
        if not isinstance(reference, dict) or set(reference) != required_reference:
            raise ManifestError(f"{case_id}.reference must contain {sorted(required_reference)}")
        if reference["basis"] not in ALLOWED_BASES:
            raise ManifestError(f"{case_id}.reference.basis is invalid")
        if reference["unit"] != "IRR":
            raise ManifestError(f"{case_id}.reference.unit must be IRR")
        for key in ("source_ids", "rule_locators", "effective_or_applicability_dates", "operator_order"):
            if not isinstance(reference[key], list) or not all(
                isinstance(value, str) and value for value in reference[key]
            ):
                raise ManifestError(f"{case_id}.reference.{key} must be a string list")
        for key in ("authority_status", "derivation", "review_status"):
            if not isinstance(reference[key], str) or not reference[key]:
                raise ManifestError(f"{case_id}.reference.{key} must be a non-empty string")
        reviewer = reference["reviewer"]
        if reviewer is not None and (not isinstance(reviewer, str) or not reviewer):
            raise ManifestError(f"{case_id}.reference.reviewer must be string or null")
        _validate_expectation(case.get("expected"), f"{case_id}.expected")
        limitations = case.get("accepted_limitations")
        if not isinstance(limitations, list) or not all(
            isinstance(value, str) and value for value in limitations
        ):
            raise ManifestError(f"{case_id}.accepted_limitations must be a string list")
        deviation = case.get("known_deviation")
        if deviation is not None:
            if not isinstance(deviation, dict) or set(deviation) != {
                "finding_ids",
                "description",
                "gate_treatment",
                "observed",
            }:
                raise ManifestError(f"{case_id}.known_deviation has invalid keys")
            if deviation["gate_treatment"] != "ACCEPTED_FOR_DRIFT_ONLY_RELEASE_BLOCKING":
                raise ManifestError(f"{case_id}.known_deviation gate treatment is invalid")
            if not isinstance(deviation["description"], str) or not deviation["description"]:
                raise ManifestError(f"{case_id}.known_deviation.description is invalid")
            if not isinstance(deviation["finding_ids"], list) or not all(
                isinstance(value, str) and value for value in deviation["finding_ids"]
            ):
                raise ManifestError(f"{case_id}.known_deviation.finding_ids is invalid")
            _validate_expectation(deviation["observed"], f"{case_id}.known_deviation.observed")
    return manifest, cases


def _path_value(row: dict[str, Any], path: str) -> Any:
    value: Any = row
    for component in path.split("."):
        if not isinstance(value, dict) or component not in value:
            return MISSING
        value = value[component]
    return value


def _display(value: Any) -> Any:
    return "<MISSING>" if value is MISSING else value


def _failure(path: str, expected: Any, actual: Any, reason: str = "not equal") -> dict[str, Any]:
    return {"path": path, "expected": expected, "actual": _display(actual), "reason": reason}


def _compare_trace(row: dict[str, Any], assertion: dict[str, Any]) -> dict[str, Any] | None:
    path = assertion["path"]
    actual = _path_value(row, path)
    expected = assertion["value"]
    operator = assertion["operator"]
    if actual is MISSING:
        return _failure(path, expected, actual, "field missing")
    if operator == "equals":
        matches = actual == expected
    elif operator == "contains":
        matches = isinstance(actual, (list, str, dict)) and expected in actual
    elif operator == "contains_all":
        matches = isinstance(actual, list) and isinstance(expected, list) and all(
            item in actual for item in expected
        )
    else:
        try:
            matches = _money(actual, f"observed.{path}") == _money(expected, f"expected.{path}")
        except ManifestError:
            matches = False
    return None if matches else _failure(path, expected, actual, f"operator {operator} failed")


def compare_expectation(row: dict[str, Any], expected: dict[str, Any]) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []

    def exact(path: str, wanted: Any, actual: Any) -> None:
        if actual != wanted:
            failures.append(_failure(path, wanted, actual))

    process = row.get("process") if isinstance(row.get("process"), dict) else {}
    exact("process.review_exit", expected["process"]["review_exit"], process.get("review_exit", MISSING))
    exact("process.calc_exit", expected["process"]["calc_exit"], process.get("calc_exit", MISSING))
    exact("review_decision", expected["review_decision"], row.get("decision", MISSING))
    exact("classification", expected["classification"], row.get("review_branch", MISSING))
    authorization = row.get("authorization") if isinstance(row.get("authorization"), dict) else {}
    for key, wanted in expected["authorization"].items():
        exact(f"authorization.{key}", wanted, authorization.get(key, MISSING))
    calculation = expected["calculation"]
    exact("calculation.present", calculation["present"], row.get("calculation_present", MISSING))
    exact("calculation.status", calculation["status"], row.get("status", MISSING))
    for key in ("payable_irr", "payable_scenarios_irr"):
        actual = row.get(key, MISSING)
        wanted = calculation[key]
        try:
            if key == "payable_scenarios_irr":
                normalized_actual = None if actual is None else [
                    _money(value, f"observed.{key}") for value in actual
                ]
                normalized_wanted = None if wanted is None else [
                    _money(value, f"expected.{key}") for value in wanted
                ]
            else:
                normalized_actual = _money(actual, f"observed.{key}")
                normalized_wanted = _money(wanted, f"expected.{key}")
            if normalized_actual != normalized_wanted:
                failures.append(_failure(f"calculation.{key}", wanted, actual))
        except (ManifestError, TypeError):
            failures.append(_failure(f"calculation.{key}", wanted, actual, "invalid exact IRR value"))
    blocking = expected["blocking_uncertainties"]
    exact("blocking_uncertainties.review", blocking["review"], row.get("live_uncertainties", MISSING))
    exact(
        "blocking_uncertainties.calculation",
        blocking["calculation"],
        row.get("calculation_blocking_uncertainties", MISSING),
    )
    for assertion in expected["trace_assertions"]:
        failure = _compare_trace(row, assertion)
        if failure:
            failures.append(failure)
    return failures


def compare(
    manifest_path: Path,
    observation_path: Path,
    case_root: Path,
    model_root: Path | None = None,
) -> tuple[dict[str, Any], bool]:
    manifest, references = load_manifest(manifest_path)
    observation = _load_json(observation_path)
    if not isinstance(observation, dict):
        raise ManifestError("observation must be an object")
    target_root = (model_root or Path.cwd()).resolve()
    model_revision, model_tree, checked_scope, provenance_profile = (
        _validate_model_binding(observation, target_root)
    )
    observed = _unique_rows(observation.get("supported_path"), "case", "observation cases")
    case_paths = {path.stem: path for path in sorted(case_root.glob("inspection-*.json"))}
    expected_ids = set(references)
    for label, actual_ids in (("observation", set(observed)), ("case files", set(case_paths))):
        if actual_ids != expected_ids:
            raise ManifestError(
                f"{label} case-set mismatch: missing={sorted(expected_ids - actual_ids)}, "
                f"unexpected={sorted(actual_ids - expected_ids)}"
            )

    rows: list[dict[str, Any]] = []
    gate_ok = True
    for case_id in sorted(references):
        reference = references[case_id]
        row = observed[case_id]
        actual_digest = hashlib.sha256(case_paths[case_id].read_bytes()).hexdigest()
        digest_failures: list[dict[str, Any]] = []
        if actual_digest != reference["input_sha256"]:
            digest_failures.append(
                _failure("input_sha256", reference["input_sha256"], actual_digest, "stale case digest")
            )
        if row.get("sha256") != actual_digest:
            digest_failures.append(
                _failure("observation.sha256", actual_digest, row.get("sha256", MISSING), "observation does not describe current case bytes")
            )
        standalone_evidence, standalone_failures = _standalone_calculation_evidence(row)
        integrity_failures = digest_failures + standalone_failures
        reference_failures = integrity_failures + compare_expectation(
            row, reference["expected"]
        )
        deviation = reference.get("known_deviation")
        deviation_failures: list[dict[str, Any]] | None = None
        if not reference_failures:
            verdict = "MATCH"
            gate_treatment = "ACCEPTED"
        elif deviation is not None and not integrity_failures:
            deviation_failures = compare_expectation(row, deviation["observed"])
            if not deviation_failures:
                verdict = "KNOWN_DEVIATION"
                gate_treatment = "ACCEPTED_FOR_DRIFT_ONLY_RELEASE_BLOCKING"
            else:
                verdict = "MISMATCH"
                gate_treatment = "REJECTED"
                gate_ok = False
        else:
            verdict = "MISMATCH"
            gate_treatment = "REJECTED"
            gate_ok = False
        assertion_paths = {
            assertion["path"] for assertion in reference["expected"]["trace_assertions"]
        }
        if deviation is not None:
            assertion_paths.update(
                assertion["path"] for assertion in deviation["observed"]["trace_assertions"]
            )
        rows.append(
            {
                "case_id": case_id,
                "input_sha256": actual_digest,
                "reference_authority": reference["reference"],
                "reference_expectation": reference["expected"],
                "observed_behavior": {
                    key: row.get(key)
                    for key in (
                        "process",
                        "decision",
                        "review_branch",
                        "authorization",
                        "calculation_present",
                        "status",
                        "payable_irr",
                        "payable_scenarios_irr",
                        "live_uncertainties",
                        "calculation_blocking_uncertainties",
                        "open_hard_questions",
                        "open_blocking_questions",
                        "evidence_blocks",
                        "blocking_conditions",
                    )
                }
                | {
                    "standalone_calculation": standalone_evidence,
                    "material_trace": {
                        path: _display(_path_value(row, path))
                        for path in sorted(assertion_paths)
                    }
                },
                "known_implementation_defect": None
                if deviation is None
                else {key: deviation[key] for key in ("finding_ids", "description", "gate_treatment")},
                "reference_assertion_failures": reference_failures,
                "known_deviation_assertion_failures": deviation_failures,
                "comparison_verdict": verdict,
                "acceptance_gate": gate_treatment,
                "accepted_limitations": reference["accepted_limitations"],
            }
        )
    counts = dict(sorted(Counter(row["comparison_verdict"] for row in rows).items()))
    output = {
        "schema_version": "1.0",
        "revision": model_revision,
        "tree": model_tree,
        "python": observation.get("python"),
        "model_binding": {
            "revision": model_revision,
            "tree": model_tree,
            "profile": provenance_profile,
            "scope": list(checked_scope),
            "import_origin_relative": observation.get("import_origin_relative"),
        },
        "manifest": {
            "id": manifest.get("manifest_id"),
            "path": str(manifest_path),
            "reference_review_status": manifest.get("reference_review_status"),
        },
        "separation_of_concerns": {
            "reference_authority": "basis/provenance; never a computed verdict",
            "observed_behavior": "fresh Review and calc evidence; process exits recorded separately",
            "known_implementation_defect": "registered drift envelope; never converted to MATCH",
        },
        "historical_observation": manifest.get("historical_observation"),
        "derived_counts": counts,
        "acceptance_gate_passed": gate_ok,
        "known_deviation_policy": manifest.get("known_deviation_policy"),
        "cases": rows,
    }
    return output, gate_ok


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("observation", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("docs/case-reference-manifest-v1.json"),
    )
    parser.add_argument("--cases", type=Path, default=Path("cases"))
    parser.add_argument(
        "--model-root",
        type=Path,
        default=Path.cwd(),
        help="clean git worktree containing the exact model revision under test",
    )
    args = parser.parse_args()
    try:
        output, gate_ok = compare(
            args.manifest,
            args.observation,
            args.cases,
            model_root=args.model_root,
        )
    except ManifestError as error:
        parser.exit(2, f"comparison input error: {error}\n")
    args.output.write_text(
        json.dumps(output, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        f"wrote {len(output['cases'])} comparisons to {args.output}; "
        f"counts={output['derived_counts']}; gate={'PASS' if gate_ok else 'FAIL'}"
    )
    return 0 if gate_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
