#!/usr/bin/env python3
"""Run the bounded case corpus without changing repository state.

Supported-path cases are submitted through the documented CLI. Optional
engine-boundary probes use the repository's INTERNAL_TEST_DIRECT test helper and
are reported separately; they are not a production authorization path.
"""

from __future__ import annotations

import argparse
import copy
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any

try:
    from .inspection_provenance import (
        BASE_MODEL_PATHS,
        INTERNAL_PROBE_ORIGINS_RELATIVE,
        RUNNER_HARNESS_PATHS,
        ProvenanceError,
        case_corpus_digest_view,
        inspector_identity,
        inspector_digest_view,
        isolated_environment,
        load_model_modules,
        load_selected_file,
        model_identity,
        model_scope,
        verified_case_corpus,
        verify_object_file,
        verify_object_origin,
    )
except ImportError:  # Direct script execution.
    from inspection_provenance import (
        BASE_MODEL_PATHS,
        INTERNAL_PROBE_ORIGINS_RELATIVE,
        RUNNER_HARNESS_PATHS,
        ProvenanceError,
        case_corpus_digest_view,
        inspector_identity,
        inspector_digest_view,
        isolated_environment,
        load_model_modules,
        load_selected_file,
        model_identity,
        model_scope,
        verified_case_corpus,
        verify_object_file,
        verify_object_origin,
    )


MODEL_PATHS = BASE_MODEL_PATHS


def _command(command: list[str], root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=root,
        env=isolated_environment(root),
        text=True,
        capture_output=True,
        check=False,
    )


def _verify_import_origin(root: Path) -> str:
    result = _command(
        [
            sys.executable,
            "-c",
            "import iran_auto_claim; print(iran_auto_claim.__file__)",
        ],
        root,
    )
    if result.returncode != 0:
        raise SystemExit(f"cannot import selected model revision: {result.stderr.strip()}")
    imported = Path(result.stdout.strip()).resolve()
    expected = (root / "src" / "iran_auto_claim").resolve()
    if expected not in imported.parents:
        raise SystemExit(
            f"selected model imports resolved outside {expected}: {imported}"
        )
    return str(imported)


def _git_value(root: Path, expression: str) -> str:
    result = _command(["git", "rev-parse", expression], root)
    return result.stdout.strip() if result.returncode == 0 else "UNKNOWN"


def _model_identity(root: Path, scope: tuple[str, ...]) -> tuple[str, str]:
    try:
        return model_identity(root, scope)
    except ProvenanceError as error:
        raise SystemExit(str(error)) from error


def _supported_case(root: Path, case_path: Path) -> dict[str, Any]:
    """Observe one supported-path case without interpreting process status as authority."""

    raw = case_path.read_bytes()
    json.loads(raw)
    review = _command(
        [sys.executable, "claim.py", "review", str(case_path), "--json", "--calc"],
        root,
    )
    calc = _command([sys.executable, "claim.py", "calc", str(case_path)], root)
    parsed: dict[str, Any] | None = None
    if review.stdout.lstrip().startswith("{"):
        parsed = json.loads(review.stdout)
    decision = (parsed or {}).get("decision") or {}
    classification = (parsed or {}).get("classification") or {}
    raw_calculation = (parsed or {}).get("calculation")
    calculation_present = isinstance(raw_calculation, dict)
    calculation = raw_calculation if calculation_present else {}
    raw_authorization = calculation.get("authorization")
    authorization = raw_authorization if isinstance(raw_authorization, dict) else {}
    authorization_granted = (
        authorization.get("issuer") == "REVIEW_GATE"
        and authorization.get("decision") in {"COMPUTE", "SCENARIO_SET"}
        and isinstance(authorization.get("claim_hash"), str)
    )
    parameters: dict[str, dict[str, Any]] = {}
    for parameter in (parsed or {}).get("parameters") or []:
        if not isinstance(parameter, dict) or not isinstance(parameter.get("slot"), str):
            continue
        parameters[parameter["slot"]] = {
            key: parameter.get(key)
            for key in (
                "status",
                "value",
                "unit",
                "authority",
            )
        }
    return {
        "case": case_path.stem,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "process": {
            "review_exit": review.returncode,
            "calc_exit": calc.returncode,
        },
        # Retain the flat process keys for historical report consumers. They are
        # observations only and are never used as authorization evidence.
        "review_exit": review.returncode,
        "calc_exit": calc.returncode,
        "decision": decision.get("decision"),
        "review_branch": classification.get("branch"),
        "authorization": {
            "granted": authorization_granted,
            "issuer": authorization.get("issuer"),
            "decision": authorization.get("decision"),
            "branch": authorization.get("branch"),
            "claim_hash": authorization.get("claim_hash"),
            "blocking_conditions": authorization.get("blocking_conditions"),
        },
        "calculation_present": calculation_present,
        "open_hard_questions": decision.get("open_hard_questions"),
        "open_blocking_questions": decision.get("open_blocking_questions"),
        "evidence_blocks": decision.get("evidence_blocks"),
        "blocking_conditions": decision.get("blocking_conditions"),
        "live_uncertainties": decision.get("live_uncertainties"),
        "calculation_blocking_uncertainties": calculation.get(
            "blocking_uncertainties"
        ),
        "payable_irr": calculation.get("payable_irr"),
        "payable_scenarios_irr": calculation.get("payable_scenarios_irr"),
        "status": calculation.get("status"),
        "reason": calculation.get("reason"),
        "labels": calculation.get("labels"),
        "fields": calculation.get("fields"),
        "rule_trace": calculation.get("rule_trace"),
        "required_guards": calculation.get("required_guards"),
        "guards_executed": calculation.get("guards_executed"),
        "review_parameters": parameters,
        "review_error_codes": [
            error.get("code")
            for error in (parsed or {}).get("errors") or []
            if isinstance(error, dict) and isinstance(error.get("code"), str)
        ],
        "review_stderr": review.stderr.strip(),
        "calc_stdout": calc.stdout.strip(),
        "calc_stderr": calc.stderr.strip(),
    }


def _supported_cases(root: Path, case_root: Path) -> list[dict[str, Any]]:
    return [
        _supported_case(root, case_path)
        for case_path in sorted(case_root.glob("inspection-*.json"))
    ]


def _internal_probes_local(
    root: Path,
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    modules, origins = load_model_modules(root, ("knowledge",))
    Knowledge = modules["knowledge"].Knowledge
    shim = load_selected_file(
        root,
        "tests/admission_shim.py",
        "_inspection_selected_admission_shim",
    )
    compute = shim.compute
    shim_origin = str((root / "tests" / "admission_shim.py").resolve())
    origins.update(
        {
            "tests.admission_shim": shim_origin,
            "tests.admission_shim.compute": verify_object_file(
                compute,
                root / "tests" / "admission_shim.py",
                "internal probe compute helper",
            ),
            "tests.admission_shim.compute_authorized": verify_object_origin(
                root,
                shim.compute_authorized,
                "internal probe engine helper",
            ),
            "tests.admission_shim._authorize_fixture_case": verify_object_origin(
                root,
                shim._authorize_fixture_case,
                "internal probe authorization helper",
            ),
        }
    )

    knowledge = Knowledge.load(root)

    def partial_case(**overrides: Any) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "claim_id": "INSPECTION-INTERNAL-PARTIAL",
            "unit": "IRR",
            "classification": {"domain": "BODY", "branch": "PARTIAL_DAMAGE"},
            "regulatory_snapshot": {"iranian_year": 1404},
            "vehicle": {
                "market_value_at_event_irr": 10000,
                "insured_sum_irr": 10000,
                "production_year_shamsi": 1404,
            },
            "event": {
                "event_date": "1404-08-20",
                "awareness_date": "1404-08-20",
                "declaration_date": "1404-08-25",
                "peril": "COLLISION",
                "cause": "COLLISION",
                "valid_licence": True,
                "fault_status": "INSURED_AT_FAULT",
            },
            "damage": {
                "parts": [
                    {
                        "category": "OTHER_REPLACEMENT_PART",
                        "assessed_loss_irr": 7400,
                        "requires_replacement": True,
                    }
                ],
                "labor_irr": 0,
                "gross_damage_irr": 7400,
                "repair_total_irr": 7400,
            },
            "policy": {
                "endorsements": [],
                "franchise": {
                    "mode": "PERCENT",
                    "rate": 0.1,
                    "calculation_base": "AFTER_DEPRECIATION",
                    "source": "POLICY",
                    "source_reference": "synthetic inspection term",
                    "source_version": "1404",
                },
                "multiple_insurance": {"state": "NO", "prior_compensation": 0},
            },
            "coverage_gate": {
                "causal_relationship_established": True,
                "risk_intensified": False,
            },
            "calculation_config": {
                "rescue_cap_base": "ASSESSED_GROSS",
                "settlement_mode": "CASH",
            },
            "derived": {"article10_ratio": 1},
        }
        for key, value in overrides.items():
            if value is None:
                payload["damage"].pop(key, None)
            else:
                payload["damage"][key] = value
        return payload

    def total_case(**overrides: Any) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "claim_id": "INSPECTION-INTERNAL-TOTAL",
            "unit": "IRR",
            "classification": {"domain": "BODY", "branch": "TOTAL_LOSS"},
            "regulatory_snapshot": {"iranian_year": 1404},
            "vehicle": {
                "market_value_at_event_irr": 2000,
                "insured_sum_irr": 2000,
                "production_year_shamsi": 1404,
            },
            "event": {
                "event_date": "1404-08-20",
                "awareness_date": "1404-08-20",
                "declaration_date": "1404-08-25",
                "peril": "COLLISION",
                "cause": "COLLISION",
                "valid_licence": True,
                "fault_status": "INSURED_AT_FAULT",
            },
            "damage": {
                "parts": [
                    {
                        "category": "OTHER_REPLACEMENT_PART",
                        "assessed_loss_irr": 1600,
                        "requires_replacement": True,
                    }
                ],
                "labor_irr": 0,
                "gross_damage_irr": 1600,
                "repair_total_irr": 1600,
                "rescue_transport_actual_irr": 0,
                "rescue_for_total_loss_test_irr": 0,
            },
            "policy": {
                "endorsements": [],
                "franchise": {
                    "mode": "ABSOLUTE",
                    "absolute_irr": 100,
                    "source": "POLICY",
                    "source_reference": "synthetic inspection term",
                    "source_version": "1404",
                },
                "multiple_insurance": {"state": "NO", "prior_compensation": 0},
            },
            "coverage_gate": {
                "causal_relationship_established": True,
                "risk_intensified": False,
            },
            "calculation_config": {
                "rescue_cap_base": "ASSESSED_GROSS",
                "settlement_mode": "CASH",
            },
            "derived": {"article10_ratio": 1},
        }
        payload["vehicle"].update(overrides.get("vehicle", {}))
        payload["damage"].update(overrides.get("damage", {}))
        for key in overrides.get("drop_damage", []):
            payload["damage"].pop(key, None)
        return payload

    override = {
        "authorized": True,
        "actor": "senior-adjuster: synthetic-inspection",
        "reason": "assessment describes a write-off",
        "source": "synthetic inspection note",
        "timestamp": "2026-10-12T09:00:00+03:30",
    }
    probes: list[tuple[str, dict[str, Any], Any]] = []

    probes.append(("INT-01 rescue omitted", partial_case(), knowledge))
    payload = partial_case()
    payload["classification"].update({"branch": "TOTAL_LOSS", "override": override})
    probes.append(("INT-02 rescue omitted plus override", payload, knowledge))
    probes.append(
        (
            "INT-03 unequal rescue operands",
            partial_case(
                rescue_transport_actual_irr=200,
                rescue_for_total_loss_test_irr=0,
            ),
            knowledge,
        )
    )
    payload = partial_case(
        rescue_transport_actual_irr=200,
        repair_total_includes_rescue=True,
    )
    probes.append(("INT-04 embedded rescue", payload, knowledge))
    probes.append(
        (
            "INT-05 explicit legacy zero",
            partial_case(rescue_omission_legacy_compatibility=True),
            knowledge,
        )
    )
    probes.append(
        (
            "INT-06 rescue-derived branch conflict",
            partial_case(
                rescue_transport_actual_irr=2000,
                rescue_for_total_loss_test_irr=2000,
            ),
            knowledge,
        )
    )
    probes.append(("INT-07 missing disposition and salvage", total_case(), knowledge))
    probes.append(
        (
            "INT-08 retained salvage without value",
            total_case(vehicle={"salvage_disposition": "INSURED_RETAINS"}),
            knowledge,
        )
    )
    probes.append(
        (
            "INT-09 retained salvage explicit zero",
            total_case(
                vehicle={
                    "salvage_disposition": "INSURED_RETAINS",
                    "salvage_value_irr": 0,
                }
            ),
            knowledge,
        )
    )

    depreciation_payload = partial_case(rescue_transport_actual_irr=100000000)
    depreciation_payload["claim_id"] = "INSPECTION-INTERNAL-DEPRECIATION"
    depreciation_payload["vehicle"].update(
        {
            "production_year_shamsi": 1399,
            "market_value_at_event_irr": 8000000000,
            "insured_sum_irr": 8000000000,
        }
    )
    depreciation_payload["damage"].update(
        {
            "parts": [
                {
                    "category": "OTHER_REPLACEMENT_PART",
                    "assessed_loss_irr": 1200000000,
                    "requires_replacement": True,
                }
            ],
            "labor_irr": 400000000,
            "gross_damage_irr": 1600000000,
            "repair_total_irr": 1600000000,
        }
    )
    probes.append(("INT-10 graph numeric control", depreciation_payload, knowledge))
    changed_annual = copy.deepcopy(knowledge)
    changed_annual.rules["REG53_ART19_REPLACEMENT_PART_DEPRECIATION"]["rule_payload"][
        "annual_rate"
    ] = Decimal("0.20")
    probes.append(("INT-11 graph annual_rate 0.20", depreciation_payload, changed_annual))
    changed_maximum = copy.deepcopy(knowledge)
    changed_maximum.rules["REG53_ART19_REPLACEMENT_PART_DEPRECIATION"]["rule_payload"][
        "maximum_rate"
    ] = Decimal("0.01")
    probes.append(("INT-12 graph maximum_rate 0.01", depreciation_payload, changed_maximum))

    complete_override = partial_case(
        rescue_transport_actual_irr=200,
        rescue_for_total_loss_test_irr=200,
    )
    complete_override["classification"].update(
        {"branch": "TOTAL_LOSS", "override": override}
    )
    complete_override["policy"]["franchise"]["calculation_base"] = "SETTLEMENT_BASE"
    probes.append(("INT-13 complete operands plus override", complete_override, knowledge))

    missing_override = partial_case()
    missing_override["classification"].update(
        {"branch": "TOTAL_LOSS", "override": override}
    )
    missing_override["policy"]["franchise"]["calculation_base"] = "SETTLEMENT_BASE"
    probes.append(("INT-14 omitted rescue plus override", missing_override, knowledge))

    rows: list[dict[str, Any]] = []
    for name, payload, target_knowledge in probes:
        row: dict[str, Any] = {"probe": name, "issuer": "INTERNAL_TEST_DIRECT"}
        try:
            result = compute(copy.deepcopy(payload), target_knowledge)
            row.update(
                {
                    "branch": result.branch,
                    "status": result.status or "SETTLED",
                    "reason": result.reason,
                    "payable_irr": None
                    if result.payable is None
                    else str(result.payable),
                    "payable_scenarios_irr": [str(value) for value in result.payable_scenarios],
                    "labels": sorted(result.labels),
                    "fields": {
                        key: str(result.fields[key])
                        for key in (
                            "classification_rescue",
                            "classification_rescue_source",
                            "depreciation",
                            "combined_for_threshold",
                            "threshold_value",
                            "is_total",
                            "settlement_base",
                            "base_after_salvage",
                            "salvage_deducted",
                            "franchise",
                            "allowable_rescue_transport",
                            "depreciation_source",
                        )
                        if key in result.fields
                    },
                }
            )
        except Exception as error:  # Escaping the boundary is an observed result.
            row.update(
                {
                    "status": f"UNCAUGHT-{type(error).__name__}",
                    "reason": str(error),
                }
            )
        rows.append(row)
    return rows, origins


def _internal_probes(
    root: Path,
    expected_revision: str,
    expected_tree: str,
    expected_harness: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, str], dict[str, Any]]:
    result = _command(
        [
            sys.executable,
            str(Path(__file__).resolve()),
            "--root",
            str(root),
            "--_internal-worker",
        ],
        root,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise SystemExit(f"internal probe worker failed provenance checks: {detail}")
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise SystemExit("internal probe worker returned malformed evidence") from error
    rows = payload.get("rows")
    origins = payload.get("import_origins")
    if not isinstance(rows, list) or len(rows) != 14 or not isinstance(origins, dict):
        raise SystemExit("internal probe worker returned incomplete evidence")
    if payload.get("revision") != expected_revision or payload.get("tree") != expected_tree:
        raise SystemExit("internal probe worker model identity changed during inspection")
    worker_harness = payload.get("inspector")
    if not isinstance(worker_harness, dict) or inspector_digest_view(
        worker_harness
    ) != inspector_digest_view(expected_harness):
        raise SystemExit("internal probe worker harness differs from the parent inspector")
    return rows, origins, worker_harness


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--cases", type=Path, default=Path("cases"))
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--internal",
        action="store_true",
        help="also run separately labelled INTERNAL_TEST_DIRECT containment probes",
    )
    parser.add_argument("--_internal-worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    root = args.root.resolve()
    if args._internal_worker:
        try:
            harness = inspector_identity(Path(__file__), RUNNER_HARNESS_PATHS)
            revision, tree = model_identity(root, model_scope(True))
            rows, origins = _internal_probes_local(root)
        except ProvenanceError as error:
            raise SystemExit(str(error)) from error
        print(
            json.dumps(
                {
                    "revision": revision,
                    "tree": tree,
                    "inspector": harness,
                    "rows": rows,
                    "import_origins": origins,
                },
                ensure_ascii=False,
            )
        )
        return 0
    case_root = args.cases.resolve()
    scope = model_scope(args.internal)
    try:
        harness = inspector_identity(Path(__file__), RUNNER_HARNESS_PATHS)
        case_inputs, captured_cases = verified_case_corpus(case_root)
    except ProvenanceError as error:
        raise SystemExit(str(error)) from error
    import_origin = _verify_import_origin(root)
    revision, tree = _model_identity(root, scope)
    with tempfile.TemporaryDirectory(prefix="iran-claim-inspection-") as temporary:
        snapshot_root = Path(temporary)
        for name, raw in captured_cases.items():
            (snapshot_root / name).write_bytes(raw)
        cases = _supported_cases(root, snapshot_root)
    report: dict[str, Any] = {
        "revision": revision,
        "tree": tree,
        "python": sys.version.split()[0],
        "inspector": harness,
        "case_inputs": case_inputs,
        "execution_profile": {
            "supported_review": {
                "count": 47,
                "acceptance_gate": True,
                "assertion_source": "reference_manifest",
            },
            "internal_test_direct": {
                "count": 14 if args.internal else 0,
                "acceptance_gate": False,
                "role": "DIAGNOSTIC_NOT_OUTCOME_VALIDATED",
            },
        },
        "import_origin": import_origin,
        "import_origin_relative": str(
            Path(import_origin).resolve().relative_to(root)
        ),
        "provenance_profile": (
            "SUPPORTED_PLUS_INTERNAL" if args.internal else "SUPPORTED_ONLY"
        ),
        "model_scope": list(scope),
        "supported_path": cases,
    }
    if args.internal:
        internal_rows, internal_origins, worker_harness = _internal_probes(
            root, revision, tree, harness
        )
        report["internal_test_direct"] = internal_rows
        report["internal_probe_worker_inspector"] = worker_harness
        report["internal_probe_import_origins"] = internal_origins
        internal_relative = {
            label: str(Path(origin).resolve().relative_to(root))
            for label, origin in internal_origins.items()
        }
        if internal_relative != INTERNAL_PROBE_ORIGINS_RELATIVE:
            raise SystemExit(
                "internal probe module origins differ from the required provenance map"
            )
        report["internal_probe_import_origins_relative"] = internal_relative
        report["internal_probe_policy"] = {
            "role": "DIAGNOSTIC_NOT_OUTCOME_VALIDATED",
            "acceptance_gate": False,
            "outcome_assertions": None,
            "structural_requirement": "14 uniquely named probe rows",
        }
    ending_revision, ending_tree = _model_identity(root, scope)
    if (ending_revision, ending_tree) != (revision, tree):
        raise SystemExit("model identity changed while inspection was running")
    try:
        ending_harness = inspector_identity(Path(__file__), RUNNER_HARNESS_PATHS)
        ending_case_inputs, ending_cases = verified_case_corpus(case_root)
    except ProvenanceError as error:
        raise SystemExit(str(error)) from error
    if inspector_digest_view(ending_harness) != inspector_digest_view(harness):
        raise SystemExit("inspection harness identity changed while inspection was running")
    if case_corpus_digest_view(ending_case_inputs) != case_corpus_digest_view(
        case_inputs
    ) or ending_cases != captured_cases:
        raise SystemExit("case input bytes changed while inspection was running")
    rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8", newline="\n")
        print(
            f"wrote {len(cases)} supported cases"
            + (" and 14 internal probes" if args.internal else "")
            + f" to {args.output}"
        )
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
