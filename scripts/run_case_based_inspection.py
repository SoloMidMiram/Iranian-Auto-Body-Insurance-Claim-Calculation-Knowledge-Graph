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
import os
from pathlib import Path
import subprocess
import sys
from typing import Any


def _command(command: list[str], root: Path) -> subprocess.CompletedProcess[str]:
    environment = dict(os.environ)
    root_src = str((root / "src").resolve())
    inherited = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = (
        root_src if not inherited else os.pathsep.join((root_src, inherited))
    )
    return subprocess.run(
        command,
        cwd=root,
        env=environment,
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


def _supported_cases(root: Path, case_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for case_path in sorted(case_root.glob("inspection-*.json")):
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
        calculation = (parsed or {}).get("calculation") or {}
        rows.append(
            {
                "case": case_path.stem,
                "sha256": hashlib.sha256(raw).hexdigest(),
                "review_exit": review.returncode,
                "calc_exit": calc.returncode,
                "decision": decision.get("decision"),
                "review_branch": classification.get("branch"),
                "open_hard_questions": decision.get("open_hard_questions"),
                "open_blocking_questions": decision.get("open_blocking_questions"),
                "evidence_blocks": decision.get("evidence_blocks"),
                "blocking_conditions": decision.get("blocking_conditions"),
                "live_uncertainties": decision.get("live_uncertainties"),
                "payable_irr": calculation.get("payable_irr"),
                "payable_scenarios_irr": calculation.get("payable_scenarios_irr"),
                "status": calculation.get("status"),
                "reason": calculation.get("reason"),
                "labels": calculation.get("labels"),
                "fields": calculation.get("fields"),
                "rule_trace": calculation.get("rule_trace"),
                "required_guards": calculation.get("required_guards"),
                "guards_executed": calculation.get("guards_executed"),
                "review_stderr": review.stderr.strip(),
                "calc_stdout": calc.stdout.strip(),
                "calc_stderr": calc.stderr.strip(),
            }
        )
    return rows


def _internal_probes(root: Path) -> list[dict[str, Any]]:
    sys.path.insert(0, str(root / "src"))
    sys.path.insert(0, str(root))
    from iran_auto_claim.knowledge import Knowledge
    from tests.admission_shim import compute

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
    return rows


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
    args = parser.parse_args()
    root = args.root.resolve()
    case_root = args.cases.resolve()
    import_origin = _verify_import_origin(root)
    cases = _supported_cases(root, case_root)
    if len(cases) != 47:
        raise SystemExit(f"expected 47 inspection cases, found {len(cases)}")
    report: dict[str, Any] = {
        "revision": _git_value(root, "HEAD"),
        "tree": _git_value(root, "HEAD^{tree}"),
        "python": sys.version.split()[0],
        "import_origin": import_origin,
        "supported_path": cases,
    }
    if args.internal:
        report["internal_test_direct"] = _internal_probes(root)
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
