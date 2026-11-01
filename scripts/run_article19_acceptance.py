"""Independent synthetic S03-S08 operands and Review observations, no goldens rewritten."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    sys.path.insert(0, str(root / "src"))
    from iran_auto_claim.admission import _internal_test_direct_authorize
    from iran_auto_claim.case import Case
    from iran_auto_claim.classify import classify
    from iran_auto_claim.engine import compute
    from iran_auto_claim.knowledge import Knowledge
    from iran_auto_claim.review import Review
    kb = Knowledge(root)
    base = {
        "claim_id": "ARTICLE19-SYNTHETIC", "unit": "IRR",
        "classification": {"branch": "TOTAL_LOSS"},
        "event": {"event_date": "1405-01-01"},
        "coverage_gate": {"causal_relationship_established": True},
        "vehicle": {"market_value_at_event_irr": 2000, "insured_sum_irr": 2000,
                    "salvage_disposition": "INSURED_RETAINS", "salvage_value_irr": 300},
        "damage": {"repair_total_irr": 1600, "rescue_for_total_loss_test_irr": 0},
        "policy": {"policy_version": "STAGE0-v1", "multiple_insurance": {"state": "NO", "prior_compensation": 0},
                   "franchise": {"mode": "ABSOLUTE", "absolute_irr": 100, "source": "POLICY",
                                 "source_reference": "Stage 0 control schedule", "source_version": "STAGE0-v1"}},
    }
    rows = []
    review_files = {"S03": "inspection-c42-at-7500.json", "S04": "inspection-c44-rescue-crosses-7600.json",
                    "S05": "inspection-c63-retains-after-salvage.json", "S06": "inspection-c61-title-not-transferred.json",
                    "S07": "inspection-c66-disposition-unresolved.json", "S08": "inspection-c65-retains-salvage-missing.json"}
    cases_root = Path(__file__).resolve().parents[1] / "cases"
    for case_id in review_files:
        payload = copy.deepcopy(base)
        if case_id in ("S03", "S04"):
            payload["vehicle"].update(market_value_at_event_irr=10000, insured_sum_irr=10000)
            payload["damage"].update(repair_total_irr=7500 if case_id == "S03" else 7400,
                                     rescue_for_total_loss_test_irr=0 if case_id == "S03" else 200)
            payload.pop("policy")  # Classification must not depend on settlement authority.
            result = classify(Case(payload), kb)
        else:
            if case_id == "S06":
                payload["vehicle"].update(salvage_disposition="INSURER_TAKES_TITLE", title_transferred=False)
            elif case_id == "S07":
                payload["vehicle"].pop("salvage_disposition")
                payload["vehicle"].pop("salvage_value_irr")
            elif case_id == "S08":
                payload["vehicle"].pop("salvage_value_irr")
            result = compute(_internal_test_direct_authorize(payload, purpose="ARTICLE19_SYNTHETIC_ORACLE"), kb).to_dict()
        review_input = json.loads((cases_root / review_files[case_id]).read_text(encoding="utf-8"))
        review = Review(review_input, kb)
        observed = review.calculate()
        rows.append({"case": case_id, "direct_input": payload, "direct_result": result,
                     "direct_input_sha256": hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest(),
                     "review_input": review_input, "review_file": review_files[case_id],
                     "review_decision": review.decision(), "review_classification": review.classification(),
                     "review_result": None if observed is None else observed.to_dict(),
                     "qualification": "Review inspection inputs differ in scale/terms from exact direct software oracle."})
    output = {"revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
              "interpreter": sys.version, "cases": rows}
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    print("wrote six classified/direct and six Review observations", args.output)


if __name__ == "__main__":
    main()
