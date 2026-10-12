#!/usr/bin/env python3
"""Combine the independent reference manifest with an inspection observation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


REFERENCE = {
    "inspection-c13a-repair-only": ("PARTIAL_DAMAGE; authorize; depreciation 0; payable 1540000000", "MATCH", "CONFIRMED_REFERENCE"),
    "inspection-c13b-replaced-but-flag-false": ("PARTIAL_DAMAGE; authorize; depreciation 0; payable 1540000000", "MATCH", "CONFIRMED_REFERENCE"),
    "inspection-c13c-repair-only-flag-true": ("contradictory input; no authorization or payable", "MATCH", "CONFIRMED_REFERENCE"),
    "inspection-c13d-replacement-control": ("PARTIAL_DAMAGE; depreciation 120000000; payable 1432000000", "MATCH", "CONFIRMED_REFERENCE"),
    "inspection-c21mix-four-kinds": ("PARTIAL_DAMAGE; depreciation only on replaced non-glass part; payable 2332000000", "MATCH", "CONFIRMED_REFERENCE"),
    "inspection-c31u04-unresolved": ("no single payable; three battery/tyre modes remain authority-dependent", "MATCH", "UNRESOLVED_AUTHORITY"),
    "inspection-c32u04-cap-then-dep": ("no single payable; token alone is not an authority artifact", "MATCH", "UNSUPPORTED_SCOPE"),
    "inspection-c33u04-dep-then-cap": ("no single payable; token alone is not an authority artifact", "MATCH", "UNSUPPORTED_SCOPE"),
    "inspection-c34u04-cap-only": ("no single payable; token alone is not an authority artifact", "MATCH", "UNSUPPORTED_SCOPE"),
    "inspection-c35q404-battery-new-price": ("new-price and interaction slots should bind; otherwise no single payable", "DISCREPANCY", "UNSUPPORTED_SCOPE"),
    "inspection-c41-below-7499": ("PARTIAL_DAMAGE at 74.99%; payable 6759", "MATCH", "CONFIRMED_REFERENCE"),
    "inspection-c42-at-7500": ("PARTIAL_DAMAGE at strict equality; payable 6760", "MATCH", "CONFIRMED_REFERENCE"),
    "inspection-c43-above-7501": ("TOTAL_LOSS; no authorization without disposition/salvage evidence", "MATCH", "INCOMPLETE_CASE_EVIDENCE"),
    "inspection-c44-rescue-crosses-7600": ("TOTAL_LOSS; rescue counted once; no authorization without total-loss evidence", "MATCH", "INCOMPLETE_CASE_EVIDENCE"),
    "inspection-c45-rescue-omitted": ("classification rescue unknown; no payable", "MATCH", "INCOMPLETE_CASE_EVIDENCE"),
    "inspection-c46-rescue-explicit-zero": ("PARTIAL_DAMAGE; explicit zero differs from omission; payable 6660", "MATCH", "CONFIRMED_REFERENCE"),
    "inspection-c47-aggregate-only-rescue": ("TOTAL_LOSS; rescue counted once; block on missing itemisation/disposition evidence", "MATCH", "INCOMPLETE_CASE_EVIDENCE"),
    "inspection-c48-assessed-depreciation-figure": ("declared assessed-figure route has no usable money binding; no supported amount", "DISCREPANCY", "UNSUPPORTED_SCOPE"),
    "inspection-c61-title-not-transferred": ("INSURER_TAKES_TITLE without completed transfer; no payable", "DISCREPANCY", "CONFIRMED_MODEL_DEFECT_IA05"),
    "inspection-c62-title-transferred": ("completed insurer-title route; no salvage deduction; payable 7200000000", "MATCH", "CONFIRMED_REFERENCE"),
    "inspection-c63-retains-after-salvage": ("retained salvage deducted before franchise; payable 6300000000", "MATCH", "CONFIRMED_REFERENCE"),
    "inspection-c64-retains-settlement-base": ("no single payable until franchise-base authority is accepted", "DISCREPANCY", "UNRESOLVED_AUTHORITY"),
    "inspection-c65-retains-salvage-missing": ("retained salvage without valuation; no authorization or payable", "MATCH", "INCOMPLETE_CASE_EVIDENCE"),
    "inspection-c66-disposition-unresolved": ("unresolved disposition; no authorization or payable", "MATCH", "INCOMPLETE_CASE_EVIDENCE"),
    "inspection-c67-disposition-not-applicable": ("physical total loss with NOT_APPLICABLE remains blocked pending RQ-07", "DISCREPANCY", "UNRESOLVED_AUTHORITY"),
    "inspection-c71-underinsured-unresolved": ("no single payable; preserve two named operator-order scenarios", "MATCH", "UNRESOLVED_AUTHORITY"),
    "inspection-c72-underinsured-order-locked": ("no single payable; bare selection token is not an authority artifact", "DISCREPANCY", "UNRESOLVED_AUTHORITY"),
    "inspection-c73-overinsured": ("ratio capped at one; PARTIAL_DAMAGE payable 6760", "MATCH", "CONFIRMED_REFERENCE"),
    "inspection-c74-underinsured-total-loss": ("total-loss base min(market, insured), no second ratio; payable 5400000000", "MATCH", "IMPLEMENTATION_INFERENCE"),
    "inspection-c81-risk-intensified-yes": ("U15 premium-ratio mechanism unresolved; no payable", "MATCH", "UNRESOLVED_AUTHORITY"),
    "inspection-c82-risk-intensified-unknown": ("material policy fact unknown; no authorization", "MATCH", "INCOMPLETE_CASE_EVIDENCE"),
    "inspection-c83-instalment-overdue": ("consequence not source-bound; no payable", "MATCH", "UNRESOLVED_AUTHORITY"),
    "inspection-c84-policy-state-unknown": ("material policy state unknown; no authorization", "MATCH", "INCOMPLETE_CASE_EVIDENCE"),
    "inspection-c91-prior-full-compensation": ("prior recovery containment; no payable", "MATCH", "CONFIRMED_REFERENCE"),
    "inspection-c92-prior-zero-documented": ("documented zero recovery; payable 1432000000", "MATCH", "CONFIRMED_REFERENCE"),
    "inspection-c93-causation-asserted-only": ("covered-peril causation not established; no authorization", "MATCH", "CONFIRMED_REFERENCE"),
    "inspection-c94-event-date-impossible": ("invalid date; structured refusal", "MATCH", "CONFIRMED_REFERENCE"),
    "inspection-c95-production-year-future": ("impossible chronology; structured refusal", "MATCH", "CONFIRMED_REFERENCE"),
    "inspection-c96-conflicting-money-aliases": ("conflicting aliases; structured refusal", "MATCH", "CONFIRMED_REFERENCE"),
    "inspection-c97-late-notice-no-excuse": ("no single payable without evidenced notice adjudication", "DISCREPANCY", "UNRESOLVED_AUTHORITY"),
    "inspection-c98-recourse-released": ("no single payable without evidenced subrogation adjudication", "DISCREPANCY", "UNRESOLVED_AUTHORITY"),
    "inspection-c99-third-party-split": ("no body-only amount without supported allocation", "MATCH", "UNRESOLVED_AUTHORITY"),
    "inspection-c101-manual-franchise-unversioned": ("unversioned manual cannot establish a monetary franchise; no payable", "DISCREPANCY", "CONFIRMED_MODEL_DEFECT_IA08"),
    "inspection-c102-glass-endorsement-token-only": ("endorsement token without complete economic wording; no single payable", "MATCH", "UNSUPPORTED_SCOPE"),
    "inspection-c104-theft-60-59-clock": ("arithmetic 7200000000; authorization unresolved while legal clock anchor is unaccepted", "DISCREPANCY", "UNRESOLVED_AUTHORITY"),
    "inspection-c105-theft-59-days": ("theft threshold not met; no payable", "MATCH", "CONFIRMED_REFERENCE"),
    "inspection-c106-theft-clock-unbound": ("unbound theft clock; no authorization or payable", "MATCH", "INCOMPLETE_CASE_EVIDENCE"),
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("observation", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    observation = json.loads(args.observation.read_text(encoding="utf-8"))
    observed = {row["case"]: row for row in observation["supported_path"]}
    if set(observed) != set(REFERENCE):
        missing = sorted(set(REFERENCE) - set(observed))
        unexpected = sorted(set(observed) - set(REFERENCE))
        raise SystemExit(f"case-set mismatch: missing={missing}, unexpected={unexpected}")

    rows = []
    for case_id in sorted(REFERENCE):
        reference, verdict, category = REFERENCE[case_id]
        row = observed[case_id]
        rows.append(
            {
                "case": case_id,
                "sha256": row["sha256"],
                "reference_outcome": reference,
                "reference_locator": "docs/CASE_BASED_INSPECTION.md sections 4 and 7",
                "observed": {
                    "review_exit": row["review_exit"],
                    "calc_exit": row["calc_exit"],
                    "decision": row["decision"],
                    "classification": row["review_branch"],
                    "authorization_granted": row["calc_exit"] == 0,
                    "status": row["status"],
                    "payable_irr": row["payable_irr"],
                    "payable_scenarios_irr": row["payable_scenarios_irr"],
                    "live_uncertainties": row["live_uncertainties"],
                    "rule_trace": row["rule_trace"],
                    "required_guards": row["required_guards"],
                    "guards_executed": row["guards_executed"],
                },
                "comparison_verdict": verdict,
                "disposition": category,
            }
        )
    output = {
        "revision": observation["revision"],
        "tree": observation["tree"],
        "python": observation["python"],
        "reference_independence": (
            "Reference outcomes were fixed in CASE_BASED_INSPECTION.md before execution; "
            "MATCH does not imply authenticated legal authority."
        ),
        "cases": rows,
    }
    args.output.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"wrote {len(rows)} comparisons to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
