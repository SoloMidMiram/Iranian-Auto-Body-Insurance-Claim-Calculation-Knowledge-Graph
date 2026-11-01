"""Reproduce S05-S10 with independent synthetic operands and both entry points.

--legacy records the pre-authority input protocol on an exact older model. It
does not pretend the older schema accepted the newly added authority records.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def inputs(case_id, legacy):
    branch = "PARTIAL_DAMAGE" if case_id in ("S09", "S10") else "TOTAL_LOSS"
    spec = {"mode": "ABSOLUTE", "absolute_irr": 100, "source": "POLICY",
            "source_reference": "S05-S10 synthetic control clause", "source_version": "TEST-v1"}
    context = {"insurer": "SYNTHETIC_INSURER", "product": "SYNTHETIC_BODY",
               "policy_reference": "CONTROL-POLICY", "policy_date": "1404-01-01",
               "contract_kind": "SYNTHETIC_TEST"}
    if not legacy and case_id != "S09":
        spec["authority"] = {
            "source_reference": spec["source_reference"], "source_version": spec["source_version"],
            "insurer": context["insurer"], "product": context["product"],
            "policy_reference": context["policy_reference"], "coverage": [branch],
            "effective_from": "1404-01-01", "effective_until": "1404-12-29",
            "source_status": "SYNTHETIC_TEST", "governs_contract": True,
            "reviewer": "software oracle author; no independent domain approval",
            "clause_locator": "explicit software control assumption",
            "document_sha256": digest(spec), "terms": copy.deepcopy(spec),
        }
        # The source label is an identity field, not an operator term.
        for field in ("source", "source_reference", "source_version"):
            spec["authority"]["terms"].pop(field)
    if case_id == "S09":
        spec = {"mode": "ABSOLUTE", "absolute_irr": 100, "source": "INSURER_MANUAL"}
    raw = {
        "claim_id": "AUTHORITY-" + case_id, "unit": "IRR",
        "classification": {"branch": branch},
        "event": {"event_date": "1404-08-20"},
        "vehicle": {"market_value_at_event_irr": 2000, "insured_sum_irr": 2000,
                    "salvage_disposition": "INSURED_RETAINS", "salvage_value_irr": 300},
        "damage": {"repair_total_irr": 1600, "rescue_for_total_loss_test_irr": 0,
                   "rescue_transport_actual_irr": 0},
        "evidence": {"EVT_SALVAGE_VALUATION": True, "EVT_TITLE_TRANSFER_PROOF": True},
        "coverage_gate": {"causal_relationship_established": True},
        "policy": {"policy_version": "TEST-v1", "franchise": spec,
                   "multiple_insurance": {"state": "NO", "prior_compensation": 0}},
    }
    if not legacy:
        raw["policy"].update(context)
    if case_id == "S06":
        raw["vehicle"].update(salvage_disposition="INSURER_TAKES_TITLE", title_transferred=False)
    if case_id == "S07":
        raw["vehicle"].pop("salvage_disposition")
        raw["vehicle"].pop("salvage_value_irr")
    if case_id == "S08":
        raw["vehicle"].pop("salvage_value_irr")
    if branch == "PARTIAL_DAMAGE":
        raw["vehicle"] = {"market_value_at_event_irr": 10000, "insured_sum_irr": 8000 if case_id == "S10" else 10000}
        raw["damage"].update(repair_total_irr=1000, gross_damage_irr=1000, assessed_depreciation_irr=0)
    if case_id == "S10":
        raw["calculation_config"] = {"article10_partial_order": "AFTER_DEPRECIATION_BEFORE_FRANCHISE"}
    return raw, context


def review_input(base, case_id, raw, context, legacy):
    payload = copy.deepcopy(base)
    payload.pop("contract_context", None)
    payload.pop("article10_order_authority", None)
    payload["claim_id"] = "REVIEW-AUTHORITY-" + case_id
    answers = payload["answers"]
    answers["Q-S0-01"] = "SYNTHETIC_INSURER / SYNTHETIC_BODY / TEST-v1"
    answers.update({"Q-S4-02": 0, "Q-S4-03": [{"category": "REPAIR_ONLY",
                    "assessed_loss": raw["damage"]["repair_total_irr"], "requires_replacement": False}],
                    "Q-S4-07": 0, "Q-S5-01": raw["vehicle"]["market_value_at_event_irr"],
                    "Q-S5-02": raw["vehicle"]["insured_sum_irr"], "Q-S6-01": "ABSOLUTE"})
    for question in ("Q-S6-02", "Q-S6-03", "Q-S6-04"):
        answers[question] = copy.deepcopy(raw["policy"]["franchise"])
    if not legacy:
        payload["contract_context"] = context
    answers["Q-S5-04"] = "UNDERINSURANCE_CLEAR" if case_id == "S10" else "NO_MATERIAL_DIFFERENCE"
    if case_id not in ("S09", "S10"):
        payload["evidence_present"] += ["EVT_SALVAGE_VALUATION", "EVT_TITLE_TRANSFER_PROOF"]
        answers["Q-S4-09"] = raw["vehicle"].get("salvage_disposition", "UNRESOLVED")
        if case_id not in ("S07", "S08"):
            answers["Q-S4-08"] = 300
        else:
            answers.pop("Q-S4-08", None)
        if case_id == "S06":
            answers["Q-S4-06"] = "NOT_TRANSFERRED"
    if case_id == "S10":
        answers["Q-S8-01"] = "AFTER_DEPRECIATION_BEFORE_FRANCHISE"
    return payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--legacy", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    sys.path.insert(0, str(root / "src"))
    from iran_auto_claim import engine
    from iran_auto_claim.admission import _internal_test_direct_authorize
    from iran_auto_claim.knowledge import Knowledge
    from iran_auto_claim.review import Review
    assert Path(engine.__file__).resolve().is_relative_to(root / "src")
    kb = Knowledge(root)
    base = json.loads((root / "cases/review_t1_fullcover_partial.json").read_text(encoding="utf-8"))
    rows = []
    for case_id in ("S05", "S06", "S07", "S08", "S09", "S10"):
        raw, context = inputs(case_id, args.legacy)
        result = engine.compute(_internal_test_direct_authorize(raw, purpose="INDEPENDENT_S05_S10_ORACLE"), kb)
        ri = review_input(base, case_id, raw, context, args.legacy)
        review = Review(ri, kb)
        observed = review.calculate()
        rows.append({"case": case_id, "direct_input": raw, "direct_input_sha256": digest(raw),
                     "direct_result": result.to_dict(), "review_input": ri, "review_input_sha256": digest(ri),
                     "review_decision": review.decision(), "review_classification": review.classification(),
                     "review_result": None if observed is None else observed.to_dict()})
    report = {"revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
              "python": sys.version, "engine_origin": str(engine.__file__), "legacy_protocol": args.legacy,
              "harness_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "cases": rows}
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    for row in rows:
        direct = row["direct_result"]
        print(row["case"], direct["payable_irr"], direct["payable_scenarios_irr"], direct["status"], row["review_decision"]["decision"])


if __name__ == "__main__":
    main()
