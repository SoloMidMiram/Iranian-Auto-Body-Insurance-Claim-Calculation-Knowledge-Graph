"""Execute RC-1 gates, retaining real exits and separately identified references."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
PACKAGE=ROOT/"docs/reconciliation-evidence/rc1-followup"
DISPOSITIONS={
"c104":("CONTRACT_AUTHORITY_PENDING","Date/event binding is consistent, but the governing clock anchor is unauthenticated. Whole-vehicle theft certification remains blocked.",["RQ-02","U13_THEFT_CLOCK_ANCHOR"]),
"c35":("ENGINEERING_DEFECT_CONFIRMED","Itemised categories failed to trigger price/interaction binding. Corrected; inline prices are not requested twice.",["IA-06","U04_BATTERY_TIRE_CAP_VS_DEPRECIATION"]),
"c48":("ENGINEERING_DEFECT_CONFIRMED","Selected assessor-figure intent silently fell back to year depreciation. Missing amount now blocks both boundaries.",["IA-09","RQ-04"]),
"c61":("INTERFACE_CONTRACT_MISMATCH","Transfer remains mandatory on this route. A blocking condition replaces the frozen uncertainty label.",["IA-05"]),
"c64":("CONTRACT_AUTHORITY_PENDING","Synthetic contract explicitly permits SETTLEMENT_BASE; real clause/circular precedence is not authenticated. That contractual scope is blocked.",["IA-13","RQ-03"]),
"c66":("CORRECT_FAIL_CLOSED_BEHAVIOR","Unknown ownership route refuses a grant instead of granting an empty scenario set. Reference review required.",["IA-14A","U12_SALVAGE_DISPOSITION"]),
"c67":("CORRECT_FAIL_CLOSED_BEHAVIOR","NOT_APPLICABLE is not an evidenced physical ownership route. Payment remains blocked; the interface label differs.",["RQ-07"]),
"c72":("CORRECT_FAIL_CLOSED_BEHAVIOR","Unsupported order token retains both scenarios without a single payable. Frozen no-grant expectation needs review.",["U01_ARTICLE10_PARTIAL_ORDER"]),
"c97":("ENGINEERING_DEFECT_CONFIRMED","A late-notice label previously coexisted with payment. Both boundaries now require adjudication, without universal exclusion or zero.",["IA-10","RQ-05"]),
"c98":("ENGINEERING_DEFECT_CONFIRMED","Recovery impairment previously only labelled payment. Both boundaries now require adjudication; documents alone are not an adjudicated decision.",["IA-10","RQ-06"]),
"c99":("OUT_OF_RELEASE_SCOPE","Third-party split classification is outside the four body branches. No body payment is granted; ordinary body precedence controls remain.",[]),
}
def git(*args):
    return subprocess.check_output(["git",*args],cwd=ROOT,text=True,encoding="utf-8").strip()
def sha(raw): return hashlib.sha256(raw).hexdigest()
def load(path): return json.loads(path.read_text(encoding="utf-8-sig"))
def write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8",newline="\n")
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True)
    out=parser.parse_args().output.resolve()
    if out.exists(): raise SystemExit("Use a fresh output directory; never overwrite pinned evidence")
    out.mkdir(parents=True)
    relative=lambda path:path.relative_to(ROOT).as_posix()
    revision=git("rev-parse","HEAD")
    preserved=["cases/inspection-*.json","docs/case-reference-manifest-v1.json","docs/reconciliation-evidence/synthetic-v1","docs/reconciliation-evidence/synthetic-reference-v1.json"]
    assert not git("diff","81ee520","HEAD","--",*preserved)
    assert not git("status","--porcelain","--untracked-files=all","--","src","knowledge","schema","tests","scripts")
    tracked=git("ls-files","--",*preserved).splitlines()
    before={n:sha((ROOT/n).read_bytes()) for n in tracked}
    env=dict(os.environ)
    env["PYTHONUTF8"]="1"
    env["TEMP"]=env["TMP"]=str(out/"tmp")
    Path(env["TEMP"]).mkdir()
    commands=[]
    def run(label,args):
        started=time.monotonic()
        result=subprocess.run([sys.executable,*args],cwd=ROOT,env=env,capture_output=True)
        raw=result.stdout+result.stderr
        (out/(label+".txt")).write_bytes(raw)
        commands.append({"label":label,"command":["python",*args],"revision":revision,"exit_code":result.returncode,"seconds":round(time.monotonic()-started,2),"output_sha256":sha(raw),"output_file":relative(out/(label+".txt"))})
        print(label,"exit",result.returncode,flush=True)
        return result.returncode
    for label,args in [
        ("compile",["-m","compileall","-q","claim.py","src","scripts"]),
        ("graph-schema",["claim.py","validate"]),
        ("fixtures",["claim.py","fixtures"]),
        ("pytest",["-m","pytest","-o","addopts=","-q","-ra","--basetemp",relative(out/"pytest")]),
        ("strict-counterexamples",["-m","pytest","-o","addopts=","-q","-ra","--runxfail","tests/test_stage0_counterexamples.py"]),
        ("properties-parity-guards",["-m","pytest","-o","addopts=","-q","tests/test_properties.py","tests/test_plans.py","tests/test_guard_paths.py"]),
        ("mutations",["scripts/run_mutation_gate.py","--check-report"]),
        ("review-docs",["scripts/sync_review_docs.py"]),
        ("faq",["scripts/sync_customer_faq.py"]),
        ("issue-dry-run",["scripts/sync_github_issues.py","--repo","SoloMidMiram/Iranian-Auto-Body-Insurance-Claim-Calculation-Knowledge-Graph"])]:
        run(label,args)
    for label,cases,manifest in [("original","cases","docs/case-reference-manifest-v1.json"),("synthetic","docs/reconciliation-evidence/synthetic-v1","docs/reconciliation-evidence/synthetic-reference-v1.json")]:
        obs=relative(out/(label+"-observation.json")); cmp=relative(out/(label+"-comparison.json"))
        if run(label+"-inspection",["scripts/run_case_based_inspection.py","--root",".","--cases",cases,*(["--internal"] if label=="original" else []),"--output",obs])==0:
            run(label+"-comparator",["scripts/build_case_comparison.py",obs,cmp,"--model-root",".","--cases",cases,"--manifest",manifest])
    if all((out/(n+"-comparison.json")).exists() for n in ("original","synthetic")):
        run("s03-s10",["scripts/run_integration_rc1_audit.py","--output",relative(out/"s03-s10"),"--original-comparison",relative(out/"original-comparison.json"),"--synthetic-comparison",relative(out/"synthetic-comparison.json")])
        original=load(out/"original-comparison.json"); synthetic=load(out/"synthetic-comparison.json")
        observed={r["case"]:r for r in load(out/"synthetic-observation.json")["supported_path"]}
        cases=[]
        for row in synthetic["cases"]:
            token=row["case_id"].split("-")[1]
            key=next((k for k in DISPOSITIONS if token.startswith(k)),None)
            if key:
                category,explanation,findings=DISPOSITIONS[key]
                cases.append({"case_id":row["case_id"],"revision":revision,"original_input":"cases/"+row["case_id"]+".json","synthetic_input":"docs/reconciliation-evidence/synthetic-v1/"+row["case_id"]+".json","synthetic_input_sha256":row["input_sha256"],"disposition":category,"explanation":explanation,"finding_ids":findings,"human_review":"PENDING","reference_authority":row["reference_authority"],"reference_expectation":row["reference_expectation"],"reference_failures":row["reference_assertion_failures"],"comparison_verdict":row["comparison_verdict"],"actual":{k:v for k,v in observed[row["case_id"]].items() if k not in ("calc_stdout","calc_stderr","review_stderr")}})
        assert len(cases)==11
        write(PACKAGE/"CASE_DISPOSITIONS.json",{"revision":revision,"independent_acceptance":"PENDING","cases":cases})
        write(PACKAGE/"corpus-summary.json",{"revision":revision,"original_counts":original["derived_counts"],"synthetic_counts":synthetic["derived_counts"],"original_gate_passed":original["acceptance_gate_passed"],"synthetic_gate_passed":synthetic["acceptance_gate_passed"],"original_input_hashes":before,"all_case_verdicts":[{"case_id":r["case_id"],"verdict":r["comparison_verdict"],"failures":r["reference_assertion_failures"]} for r in synthetic["cases"]],"diagnostics":"14 INTERNAL_TEST_DIRECT probes are structurally checked, not independent customer outcomes"})
    assert before=={n:sha((ROOT/n).read_bytes()) for n in tracked}
    assert git("rev-parse","HEAD")==revision
    summary={"revision":revision,"tree":git("rev-parse","HEAD^{tree}"),"python":sys.version,"platform":platform.platform(),"git":git("--version"),"commands":commands,"frozen_inputs_preserved":True,"engineering_checks_passed":all(r["exit_code"]==0 for r in commands if "comparator" not in r["label"]),"release_gate_passed":all(r["exit_code"]==0 for r in commands),"independent_review":"PENDING"}
    write(PACKAGE/"validation-summary.json",summary)
    lines=["# Validation report","","Executed revision: "+revision+". Python "+sys.version.split()[0]+".","Outputs are retained in the fresh local directory; exact command metadata and hashes are in validation-summary.json.","Comparator failures remain failures; successful execution checks cannot grant independent acceptance.","","| Command | Exit | Output SHA-256 |","|---|---|---|"]
    lines+=["| "+" ".join(r["command"])+" | "+str(r["exit_code"])+" | "+r["output_sha256"]+" |" for r in commands]
    lines+=["","Full pytest summary:"]+(out/"pytest.txt").read_text(encoding="utf-8",errors="replace").splitlines()[-5:]
    (PACKAGE/"VALIDATION_REPORT.md").write_text("\n".join(lines)+"\n",encoding="utf-8",newline="\n")
    return 0 if summary["release_gate_passed"] else 1
if __name__=="__main__": raise SystemExit(main())
