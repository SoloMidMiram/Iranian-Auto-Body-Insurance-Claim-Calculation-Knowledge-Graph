#!/usr/bin/env python3
"""Reproduce the bounded theft-to-total-loss override evidence investigation.

This script does not modify runtime state. Direct rows use the repository's
schema-validating INTERNAL_TEST_DIRECT authorization helper and are reported
separately from supported Review rows.
"""

from __future__ import annotations

import argparse
import copy
from datetime import date, timedelta
import json
from pathlib import Path
import sys
from typing import Any

try:
    from .inspection_provenance import (
        INVESTIGATION_HARNESS_PATHS,
        ProvenanceError,
        canonical_sha256,
        inspector_identity,
        inspector_digest_view,
        load_model_modules,
        model_identity,
        model_scope,
        public_file_identity,
        sha256_bytes,
        verified_file_identity,
        verify_object_origin,
    )
except ImportError:  # Direct script execution.
    from inspection_provenance import (
        INVESTIGATION_HARNESS_PATHS,
        ProvenanceError,
        canonical_sha256,
        inspector_identity,
        inspector_digest_view,
        load_model_modules,
        model_identity,
        model_scope,
        public_file_identity,
        sha256_bytes,
        verified_file_identity,
        verify_object_origin,
    )


OVERRIDE = {
    "authorized": True,
    "actor": "senior-adjuster: synthetic-inspection",
    "reason": "documented total-loss branch selection",
    "source": "synthetic inspection review-board record",
    "timestamp": "2026-10-12T18:00:00+03:30",
}


def _direct_base() -> dict[str, Any]:
    start = date(2026, 1, 1)
    return {
        "claim_id": "INSPECTION-OVERRIDE-DIRECT",
        "unit": "IRR",
        "classification": {
            "domain": "BODY",
            "branch": "TOTAL_LOSS",
            "override": copy.deepcopy(OVERRIDE),
        },
        "regulatory_snapshot": {"iranian_year": 1404},
        "vehicle": {
            "market_value_at_event_irr": 10000,
            "insured_sum_irr": 10000,
            "production_year_shamsi": 1404,
            "salvage_disposition": "INSURED_RETAINS",
            "salvage_value_irr": 0,
        },
        "event": {
            "event_date": "2026-01-01",
            "peril": "THEFT",
            "cause": "THEFT",
            "theft_clock": {
                "start_event": "THEFT_OCCURRENCE",
                "start_date": start.isoformat(),
                "as_of_date": (start + timedelta(days=10)).isoformat(),
                "calendar": "GREGORIAN",
                "source": "synthetic inspection police report",
            },
        },
        "damage": {
            "theft_type": "WHOLE_VEHICLE",
            "days_missing": 10,
            "gross_damage_irr": 7400,
            "repair_total_irr": 7400,
            "rescue_for_total_loss_test_irr": 0,
        },
        "policy": {
            "policy_version": "SYNTHETIC-1404",
            "multiple_insurance": {"state": "NO", "prior_compensation": 0},
            "franchise": {
                "mode": "ABSOLUTE",
                "absolute_irr": 1000,
                "source": "POLICY",
                "source_reference": "synthetic inspection policy term",
                "source_version": "SYNTHETIC-1404",
            },
        },
        "coverage_gate": {
            "causal_relationship_established": True,
            "risk_intensified": False,
        },
        "calculation_config": {
            "rescue_cap_base": "SETTLEMENT_BASE",
            "settlement_mode": "CASH",
        },
    }


def _drop(payload: dict[str, Any], *paths: tuple[str, str]) -> None:
    for section, field in paths:
        payload[section].pop(field, None)


def _direct_variants() -> list[tuple[str, dict[str, Any]]]:
    rows: list[tuple[str, dict[str, Any]]] = []

    payload = _direct_base()
    _drop(payload, ("damage", "repair_total_irr"))
    rows.append(("DIR-01 missing repair, explicit rescue zero", payload))

    payload = _direct_base()
    _drop(payload, ("vehicle", "market_value_at_event_irr"))
    rows.append(("DIR-02 missing market, repair and rescue zero present", payload))

    payload = _direct_base()
    _drop(
        payload,
        ("damage", "repair_total_irr"),
        ("vehicle", "market_value_at_event_irr"),
    )
    rows.append(("DIR-03 missing repair and market, rescue zero present", payload))

    payload = _direct_base()
    _drop(payload, ("damage", "rescue_for_total_loss_test_irr"))
    rows.append(("DIR-04 rescue omitted, repair and market present", payload))

    payload = _direct_base()
    _drop(payload, ("damage", "repair_total_irr"))
    payload["damage"]["rescue_transport_actual_irr"] = 200
    _drop(payload, ("damage", "rescue_for_total_loss_test_irr"))
    rows.append(("DIR-05 missing repair, actual rescue supplied", payload))

    payload = _direct_base()
    _drop(payload, ("damage", "repair_total_irr"))
    payload["damage"]["rescue_transport_actual_irr"] = 200
    payload["damage"]["rescue_for_total_loss_test_irr"] = 0
    rows.append(("DIR-06 missing repair, conflicting rescue operands", payload))

    rows.append(("DIR-07 complete evidence-supported override", _direct_base()))

    payload = _direct_base()
    payload["classification"] = {"domain": "BODY", "branch": "THEFT"}
    rows.append(("DIR-08 ordinary theft without override", payload))

    payload = _direct_base()
    _drop(
        payload,
        ("damage", "repair_total_irr"),
        ("damage", "rescue_for_total_loss_test_irr"),
    )
    rows.append(("DIR-09 missing repair and rescue", payload))
    return rows


def _direct_results(
    knowledge: Any, compute: Any, authorize_fixture_case: Any
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for name, payload in _direct_variants():
        row: dict[str, Any] = {
            "variant": name,
            "path": "INTERNAL_TEST_DIRECT",
            "authorization_granted": False,
        }
        try:
            authorization = authorize_fixture_case(copy.deepcopy(payload), knowledge)
            row["authorization_granted"] = True
            result = compute(authorization, knowledge)
            classification = result.fields.get("classification") or {}
            row.update(
                {
                    "classification_outcome": classification.get("outcome"),
                    "derived_branch": classification.get("derived_branch"),
                    "selected_branch": result.branch,
                    "status": result.status or "SETTLED",
                    "payable_irr": None
                    if result.payable is None
                    else str(result.payable),
                    "reason": result.reason,
                    "required_guards": result.required_guards,
                    "guards_executed": result.guards_executed,
                    "labels": sorted(result.labels),
                }
            )
        except Exception as error:
            row.update(
                {
                    "status": f"STRUCTURED-{type(error).__name__}",
                    "payable_irr": None,
                    "reason": str(error),
                }
            )
        rows.append(row)
    return rows


def _review_results(
    source: dict[str, Any],
    knowledge: Any,
    Review: Any,
    AuthorizationNotGranted: type[Exception],
    compute: Any,
) -> list[dict[str, Any]]:
    variants = []
    for name, question in (
        ("REV-01 missing repair assessment", "Q-S4-03"),
        ("REV-02 missing market value", "Q-S5-01"),
        ("REV-03 omitted rescue", "Q-S4-07"),
    ):
        payload = copy.deepcopy(source)
        payload["claim_id"] = name.split()[0]
        payload["answers"].pop(question, None)
        variants.append((name, payload))

    rows = []
    for name, payload in variants:
        review = Review(payload, knowledge)
        decision = review.decision()
        row: dict[str, Any] = {
            "variant": name,
            "path": "SUPPORTED_REVIEW",
            "decision": decision.get("decision"),
            "authorization_granted": False,
            "calculation": None,
            "open_blocking_questions": decision.get("open_blocking_questions"),
            "evidence_blocks": decision.get("evidence_blocks"),
        }
        try:
            authorization = review.authorize()
            row["authorization_granted"] = True
            result = compute(authorization, knowledge)
            row["calculation"] = {
                "status": result.status or "SETTLED",
                "payable_irr": None
                if result.payable is None
                else str(result.payable),
            }
        except AuthorizationNotGranted as error:
            row["authorization_error"] = str(error)
        rows.append(row)
    return rows


def _manifest_binding(path: Path, case_digest: str) -> tuple[dict[str, Any], bytes]:
    resolved = path.resolve()
    raw = resolved.read_bytes()
    try:
        manifest = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ProvenanceError(f"reference manifest is malformed: {resolved}: {error}") from error
    cases = manifest.get("cases") if isinstance(manifest, dict) else None
    if not isinstance(cases, list):
        raise ProvenanceError("reference manifest has no case list")
    case_id = "inspection-c104-theft-60-59-clock"
    matches = [case for case in cases if case.get("case_id") == case_id]
    if len(matches) != 1:
        raise ProvenanceError(f"reference manifest must contain exactly one {case_id}")
    expected_digest = matches[0].get("input_sha256")
    if case_digest != expected_digest:
        raise ProvenanceError(
            f"C104 input digest differs from the reference manifest: "
            f"expected {expected_digest}, observed {case_digest}"
        )
    deviations = [
        {"case_id": case.get("case_id"), "known_deviation": case.get("known_deviation")}
        for case in cases
        if case.get("known_deviation") is not None
    ]
    return (
        {
            "path": str(resolved),
            "manifest_id": manifest.get("manifest_id"),
            "sha256": sha256_bytes(raw),
            "known_deviation_envelope_sha256": canonical_sha256(deviations),
            "c104_expected_sha256": expected_digest,
        },
        raw,
    )


def _selected_runtime(root: Path) -> tuple[dict[str, Any], dict[str, str]]:
    modules, origins = load_model_modules(
        root,
        ("admission", "engine", "fixtures", "knowledge", "review"),
    )
    runtime = {
        "AuthorizationNotGranted": modules["admission"].AuthorizationNotGranted,
        "compute": modules["engine"].compute,
        "authorize_fixture_case": modules["fixtures"]._authorize_fixture_case,
        "Knowledge": modules["knowledge"].Knowledge,
        "Review": modules["review"].Review,
    }
    for label, value in runtime.items():
        origins[label] = verify_object_origin(root, value, label)
    return runtime, origins


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--cases", type=Path, default=Path("cases"))
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    scope = model_scope(False)
    try:
        harness = inspector_identity(Path(__file__), INVESTIGATION_HARNESS_PATHS)
        revision, tree = model_identity(root, scope)
        runtime, origins = _selected_runtime(root)
    except ProvenanceError as error:
        raise SystemExit(str(error)) from error
    case_root = (
        args.cases.resolve()
        if args.cases.is_absolute()
        else (root / args.cases).resolve()
    )
    case_identity = verified_file_identity(
        case_root / "inspection-c104-theft-60-59-clock.json"
    )
    try:
        source = json.loads(case_identity["bytes"])
    except json.JSONDecodeError as error:
        raise SystemExit(f"C104 input is malformed JSON: {error}") from error
    inspector_root = Path(harness["root"])
    manifest_path = (
        args.manifest.resolve()
        if args.manifest is not None
        else inspector_root / "docs" / "case-reference-manifest-v1.json"
    )
    try:
        manifest_binding, manifest_bytes = _manifest_binding(
            manifest_path, case_identity["sha256"]
        )
    except ProvenanceError as error:
        raise SystemExit(str(error)) from error
    knowledge = runtime["Knowledge"].load(root)
    report = {
        "revision": revision,
        "tree": tree,
        "python": sys.version.split()[0],
        "inspector": harness,
        "case_input": public_file_identity(case_identity),
        "reference_manifest": manifest_binding,
        "provenance_profile": "BOUNDED_OVERRIDE_INVESTIGATION",
        "model_scope": list(scope),
        "import_origins": origins,
        "import_origins_relative": {
            label: str(Path(origin).resolve().relative_to(root))
            for label, origin in origins.items()
        },
        "scope": "bounded theft-derived classification with total-loss override",
        "supported_review_limitation": (
            "Review has no input that manufactures classification.override; supported rows "
            "therefore test missing evidence without an override."
        ),
        "internal_test_direct": _direct_results(
            knowledge,
            runtime["compute"],
            runtime["authorize_fixture_case"],
        ),
        "supported_review": _review_results(
            source,
            knowledge,
            runtime["Review"],
            runtime["AuthorizationNotGranted"],
            runtime["compute"],
        ),
    }
    try:
        ending_revision, ending_tree = model_identity(root, scope)
        ending_harness = inspector_identity(Path(__file__), INVESTIGATION_HARNESS_PATHS)
    except ProvenanceError as error:
        raise SystemExit(str(error)) from error
    if (ending_revision, ending_tree) != (revision, tree):
        raise SystemExit("model identity changed while investigation was running")
    if inspector_digest_view(ending_harness) != inspector_digest_view(harness):
        raise SystemExit("inspection harness identity changed while investigation was running")
    if verified_file_identity(Path(case_identity["path"])) != case_identity:
        raise SystemExit("C104 input bytes changed while investigation was running")
    if manifest_path.read_bytes() != manifest_bytes:
        raise SystemExit("reference manifest changed while investigation was running")
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8", newline="\n")
        print(f"wrote investigation to {args.output}")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
