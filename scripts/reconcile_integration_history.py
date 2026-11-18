"""Prove one equivalent application per intended remote correction in the candidate."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BASE = "cd7fb39a0b7859f2cec91b94770e240ab62e0b75"
CANDIDATE = "5cee269bce51653adb4b1e216ee0fad15db5144e"


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True, encoding="utf-8").strip()


def delta(commit):
    # Ignore hunk locations, context and blob IDs: stacked prerequisites move them.
    # Preserve each file and every ordered added/deleted line. Generated report
    # is audited separately because it depends on the combined mutation set.
    patch = git("diff", commit + "^", commit, "--", ".", ":!docs/MUTATION_REPORT.md")
    return "\n".join(line for line in patch.splitlines() if line.startswith(("diff --git", "+", "-")))


def main():
    integrated = git("rev-list", BASE + ".." + CANDIDATE).splitlines()
    rows = []
    for pr, head in [(57, "cb7bce78e8704378539f915f5d4ffd9be943a597"), (58, "49b2446f4ac2674f5bbbd81b5d3bc513e1e77133"), (59, "1e41c67c7f892526f52aecd40267709592383444")]:
        for commit in git("rev-list", "--reverse", BASE + ".." + head).splitlines():
            expected = delta(commit)
            matches = [local for local in integrated if delta(local) == expected]
            rows.append({"pr": pr, "remote_commit": commit, "equivalent_local_commits": matches, "ordered_change_sha256": hashlib.sha256(expected.encode()).hexdigest(), "exactly_once": len(matches) == 1})
    report = {"base": BASE, "candidate": CANDIDATE, "candidate_tree": git("rev-parse", CANDIDATE + "^{tree}"), "method": "Exact ordered additions/deletions per file, omitting hunk context and blob IDs; docs/MUTATION_REPORT.md excluded as generated combined-state evidence. No approval inferred.", "rows": rows, "passed": all(row["exactly_once"] for row in rows), "executable_paths_unchanged_since_candidate": not git("diff", CANDIDATE, "HEAD", "--", "src", "knowledge", "schemas", "fixtures", "tests")}
    path = ROOT / "docs/reconciliation-evidence/integration-history.json"
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    assert report["passed"], report


if __name__ == "__main__":
    main()
