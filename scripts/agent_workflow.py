"""Read-only change inventory and compact JUnit regression comparison."""
from __future__ import annotations
import argparse
import json
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT).decode("utf-8")


def changes():
    def paths(*args):
        return [p for p in git(*args, "-z").split("\0") if p]
    return {"head": git("rev-parse", "HEAD").strip(),
            "branch": git("branch", "--show-current").strip(),
            "staged": paths("diff", "--cached", "--name-only"),
            "unstaged": paths("diff", "--name-only"),
            "untracked": paths("ls-files", "--others", "--exclude-standard"),
            "interpretation": "Paths are not ownership or approval. Inspect diffs and select an explicit upload allowlist."}


def junit(path):
    rows = {}
    for node in ET.parse(path).iter("testcase"):
        key = node.get("classname", "") + "::" + node.get("name", "")
        if key in rows:
            raise ValueError("Duplicate test identity: " + key)
        outcome, message = "passed", ""
        for tag in ("failure", "error", "skipped"):
            child = node.find(tag)
            if child is not None:
                outcome, message = tag, child.get("message", "")
                break
        rows[key] = {"outcome": outcome, "message": message[:400]}
    if not rows:
        raise ValueError("No testcase records; cannot infer passing tests")
    return rows


def regress(current, baseline=None, limit=20):
    now = junit(current)
    old = junit(baseline) if baseline else {}
    failures = [{"id": key, **value, "baseline": old.get(key, {}).get("outcome", "not-recorded")}
                for key, value in now.items() if value["outcome"] in ("failure", "error")]
    return {"current": str(current), "baseline": str(baseline) if baseline else None,
            "counts": {state: sum(r["outcome"] == state for r in now.values()) for state in ("passed", "failure", "error", "skipped")},
            "failures": failures[:limit], "failures_omitted": max(0, len(failures)-limit),
            "missing_from_current": sorted(set(old)-set(now))[:limit],
            "missing_total": len(set(old)-set(now)),
            "interpretation": "Outcome comparison only; inspect original logs for cause. Unrecorded or missing tests are not passes."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("changes")
    report = sub.add_parser("regress")
    report.add_argument("current", type=Path)
    report.add_argument("--baseline", type=Path)
    report.add_argument("--limit", type=int, choices=range(1,101), default=20, metavar="1..100")
    args = parser.parse_args()
    result = changes() if args.command == "changes" else regress(args.current, args.baseline, args.limit)
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return int(args.command == "regress" and (result["counts"]["failure"] + result["counts"]["error"] + result["missing_total"] > 0))

if __name__ == "__main__":
    raise SystemExit(main())
