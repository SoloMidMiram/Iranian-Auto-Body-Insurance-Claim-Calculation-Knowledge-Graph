"""Author a separately identified synthetic corpus; never learn expectations from results.

Only applicability evidence is supplied. Deliberately missing identity, salvage,
transfer, endorsement and other negative-case facts remain missing.
"""
import copy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]
from contract_assumptions import with_review_contract
from iran_auto_claim.knowledge import Knowledge
from iran_auto_claim.review import Review


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8", newline="\n")


def main():
    target = ROOT / "docs/reconciliation-evidence"
    corpus = target / "synthetic-v1"
    manifest = json.loads((ROOT / "docs/case-reference-manifest-v1.json").read_text(encoding="utf-8"))
    manifest["manifest_id"] = "inspection-synthetic-applicability-v1"
    manifest["reference_origin"] += " Separate synthetic applicability variant: original expected objects retained byte-for-value; no observed outputs used."
    mapping = []
    kb = Knowledge(ROOT)
    for entry in manifest["cases"]:
        name = entry["case_id"] + ".json"
        original = (ROOT / "cases" / name).read_bytes()
        payload = json.loads(original)
        try:
            authored = with_review_contract(payload, kb)
            disposition = "Explicit synthetic franchise applicability supplied; all other operands preserved."
        except ValueError:
            authored = copy.deepcopy(payload)
            disposition = "Negative identity control: no authority invented for unidentifiable terms."
        write(corpus / name, authored)
        entry["input_sha256"] = hashlib.sha256((corpus / name).read_bytes()).hexdigest()
        mapping.append({"case": entry["case_id"], "original_sha256": hashlib.sha256(original).hexdigest(), "synthetic_sha256": entry["input_sha256"], "disposition": disposition})
    write(target / "synthetic-reference-v1.json", manifest)
    write(target / "corpus-map.json", {"corpus_id": manifest["manifest_id"], "qualification": "Software assumptions only. Synthetic applicability is complete for identifiable franchise terms; intentional negative evidence gaps remain. No legal authentication or independent review claimed.", "cases": mapping})

    # Exact threshold examples, distinct from related historical inspection inputs.
    rows = []
    for label, repair, rescue, expected in [("S03", 7500, 0, "PARTIAL_DAMAGE"), ("S04", 7400, 200, "TOTAL_LOSS")]:
        payload = json.loads((corpus / "inspection-c44-rescue-crosses-7600.json").read_text(encoding="utf-8"))
        payload["claim_id"] = "SYNTHETIC-EXACT-" + label
        payload["answers"]["Q-S4-03"][0]["assessed_loss"] = repair
        payload["answers"]["Q-S4-07"] = rescue
        payload["answers"]["Q-S4-09"] = "INSURED_RETAINS" if label == "S04" else "NOT_APPLICABLE"
        if label == "S04":
            payload["answers"]["Q-S4-08"] = 0
            payload["evidence_present"].append("EVT_SALVAGE_VALUATION")
            payload["answers"]["Q-S6-02"]["calculation_base"] = "AFTER_SALVAGE"
            payload["answers"]["Q-S6-03"]["calculation_base"] = "AFTER_SALVAGE"
        payload = with_review_contract(payload, kb)
        review = Review(payload, kb)
        result = review.calculate()
        classification = review.classification()
        rows.append({"case": label, "input": payload, "expected_branch": expected, "classification": classification, "branch_matches": classification["branch"] == expected, "decision": review.decision(), "emitted_case": review.case_payload(), "result": result.to_dict() if result else None})
    write(target / "exact-s03-s04.json", rows)
    assert all(row["branch_matches"] for row in rows)
    assert all(row["decision"]["decision"] == "COMPUTE" for row in rows)
    assert [row["result"]["payable_irr"] for row in rows] == [6750, 9200]


if __name__ == "__main__":
    main()
