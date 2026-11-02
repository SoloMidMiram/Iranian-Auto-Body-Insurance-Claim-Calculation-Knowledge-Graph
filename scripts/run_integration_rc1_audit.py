"""Execute S03-S10 together and retain author dispositions without accepting references."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

def load(path):
    return json.loads(path.read_text(encoding="utf-8"))

def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    evidence = ROOT / "docs/reconciliation-evidence"
    revision = git("rev-parse", "HEAD")
    scope = ["claim.py", "pyproject.toml", "src", "knowledge", "schema", "ontology", "fixtures", "tests", "cases"]
    assert not git("diff", "5cee269", "HEAD", "--", *scope)
    assert not git("diff", "HEAD", "--", *scope)
    sys.path.insert(0, str(ROOT / "src"))
    from iran_auto_claim.knowledge import Knowledge
    from iran_auto_claim.review import Review
    import iran_auto_claim.engine as engine
    assert Path(engine.__file__).resolve().is_relative_to(ROOT / "src")
    kb = Knowledge(ROOT)
    thresholds = []
    for previous in load(evidence / "exact-s03-s04.json"):
        payload = previous["input"]
        review = Review(payload, kb)
        result = review.calculate()
        classification = review.classification()
        expected_branch, expected_amount = {"S03": ("PARTIAL_DAMAGE", 6750), "S04": ("TOTAL_LOSS", 9200)}[previous["case"]]
        assert classification["branch"] == expected_branch
        assert review.decision()["decision"] == "COMPUTE"
        assert result.payable == expected_amount
        thresholds.append({"case": previous["case"], "input": payload, "classification": classification,
                           "review_decision": review.decision(), "result": result.to_dict(),
                           "reference": {"branch": expected_branch, "payable_irr": expected_amount}})
    out.mkdir(parents=True, exist_ok=True)
    write(out / "s03-s04.json", {"revision": revision, "cases": thresholds})
    subprocess.run([sys.executable, str(ROOT / "scripts/run_settlement_authority_acceptance.py"),
                    "--root", str(ROOT), "--output", str(out / "s05-s10.json")], cwd=ROOT, check=True)
    settlement = load(out / "s05-s10.json")
    assert settlement["revision"] == revision
    assert all(row["direct_reference_matches"] for row in settlement["cases"])
    assert all(row["reference_matches"] for row in settlement["adversarial_probes"])
    for row in settlement["cases"]:
        label = row["case"]
        if label in ("S05", "S10"):
            assert row["review_result"] is not None
            assert all(row["review_result"][key] == value for key, value in row["independent_reference"].items())
            assert row["review_decision"]["decision"] == ("COMPUTE" if label == "S05" else "SCENARIO_SET")
        else:
            assert row["review_result"] is None
            assert row["review_decision"]["decision"] == "INSUFFICIENT_INFORMATION"
    original = load(evidence / "original-comparison.json")
    synthetic = load(evidence / "synthetic-comparison.json")
    synthetic_by_id = {row["case_id"]: row for row in synthetic["cases"]}
    cases = []
    for old in original["cases"]:
        new = synthetic_by_id[old["case_id"]]
        changed = old["comparison_verdict"] != "MATCH"
        if changed:
            observed = old["observed_behavior"]
            assert observed["payable_irr"] is None and observed["authorization"]["granted"] is False
            assert "FRANCHISE_AUTHORITY_REQUIRED" in observed["blocking_conditions"]
        residual = new["comparison_verdict"] != "MATCH"
        cases.append({"case_id": old["case_id"],
                      "historical_comparison": old["comparison_verdict"],
                      "historical_disposition": "EXPECTED_CONTAINMENT" if changed else "UNCHANGED",
                      "historical_reason": "Missing contract applicability blocks payment and grants; this does not dispose of underlying findings." if changed else "Original frozen expectations match.",
                      "synthetic_comparison": new["comparison_verdict"],
                      "synthetic_disposition": "UNRESOLVED_DOMAIN_ISSUE" if residual else "REFERENCE_MATCH",
                      "synthetic_reason": "Contract/interface/reference disposition requires independent review; no new regression or legal conclusion inferred." if residual else "Original frozen expectation satisfied with explicitly synthetic applicability or preserved negative evidence.",
                      "residual_assertions": new["reference_assertion_failures"],
                      "known_implementation_defect": new["known_implementation_defect"],
                      "independent_disposition": "PENDING"})
    assert len(cases) == len(synthetic_by_id) == 47
    assert Counter(row["historical_disposition"] for row in cases)["EXPECTED_CONTAINMENT"] == 41
    assert Counter(row["synthetic_disposition"] for row in cases)["UNRESOLVED_DOMAIN_ISSUE"] == 11
    write(out / "case-dispositions.json", {"executed_revision": revision,
          "corpus_observation_revision": original["revision"],
          "qualification": "Author-prepared reconciliation, not independent acceptance. No references changed. UNRESOLVED_DOMAIN_ISSUE includes engineering/interface adjudication, not merely legal ambiguity.",
          "cases": cases})
    write(out / "manifest.json", {"revision": revision, "tree": git("rev-parse", "HEAD^{tree}"),
          "engine_origin": str(engine.__file__), "python": sys.version,
          "all_s03_s10_assertions_passed": True, "independent_acceptance": "PENDING", "release": "BLOCKED",
          "inputs_and_outputs_sha256": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
              for path in [out / "s03-s04.json", out / "s05-s10.json", out / "case-dispositions.json",
                           evidence / "original-comparison.json", evidence / "synthetic-comparison.json"]}})
    print("PASS: S03-S10 at", revision, "; 47 author dispositions; independent acceptance PENDING")

if __name__ == "__main__":
    main()
