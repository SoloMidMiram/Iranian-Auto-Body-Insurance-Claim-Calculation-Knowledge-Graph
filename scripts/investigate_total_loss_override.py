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
import subprocess
import sys
from typing import Any

from iran_auto_claim.admission import AuthorizationNotGranted
from iran_auto_claim.engine import compute
from iran_auto_claim.fixtures import _authorize_fixture_case
from iran_auto_claim.knowledge import Knowledge
from iran_auto_claim.review import Review


OVERRIDE = {
    "authorized": True,
    "actor": "senior-adjuster: synthetic-inspection",
    "reason": "documented total-loss branch selection",
    "source": "synthetic inspection review-board record",
    "timestamp": "2026-10-12T18:00:00+03:30",
}


def _git_value(root: Path, expression: str) -> str:
    result = subprocess.run(
        ["git", "rev-parse", expression],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else "UNKNOWN"


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


def _direct_results(knowledge: Knowledge) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for name, payload in _direct_variants():
        row: dict[str, Any] = {
            "variant": name,
            "path": "INTERNAL_TEST_DIRECT",
            "authorization_granted": False,
        }
        try:
            authorization = _authorize_fixture_case(copy.deepcopy(payload), knowledge)
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
    case_root: Path, knowledge: Knowledge
) -> list[dict[str, Any]]:
    source = json.loads(
        (case_root / "inspection-c104-theft-60-59-clock.json").read_text(
            encoding="utf-8"
        )
    )
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--cases", type=Path, default=Path("cases"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    knowledge = Knowledge.load(root)
    report = {
        "revision": _git_value(root, "HEAD"),
        "tree": _git_value(root, "HEAD^{tree}"),
        "python": sys.version.split()[0],
        "scope": "bounded theft-derived classification with total-loss override",
        "supported_review_limitation": (
            "Review has no input that manufactures classification.override; supported rows "
            "therefore test missing evidence without an override."
        ),
        "internal_test_direct": _direct_results(knowledge),
        "supported_review": _review_results(args.cases.resolve(), knowledge),
    }
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8", newline="\n")
        print(f"wrote investigation to {args.output}")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
