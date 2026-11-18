"""Bounded, read-only context retrieval. Never runs tests or remote mutations."""
from __future__ import annotations
import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
SCOPES = ("src", "knowledge", "tests", "scripts", "planning")


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True, encoding="utf-8").strip()


def brief():
    status = git("status", "--porcelain").splitlines()
    print(json.dumps({"branch": git("branch", "--show-current"), "head": git("rev-parse", "HEAD"),
        "working_tree_entries": len(status), "dirty": bool(status),
        "context": ["docs/PROJECT_CONTEXT.md", "docs/ITERATION_ROADMAP.md", "docs/REPO_MAP.md"],
        "validation": "Historical results must be matched to their candidate manifest; no tests run by this command."}, indent=2))
    print(git("diff", "--stat"))


def find(keyword, limit):
    if shutil.which("rg"):
        proc = subprocess.Popen(["rg", "-n", "-F", "--glob", "*.py", "--glob", "*.json", "--", keyword, *SCOPES],
            cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")
        count = 0
        try:
            for line in proc.stdout:
                if count == limit:
                    print("[output limited; narrow the keyword/path for more]")
                    proc.terminate()
                    break
                print(line.rstrip()[:600])
                count += 1
        finally:
            proc.wait()
        if proc.returncode not in (0, 1) and count < limit:
            raise RuntimeError(proc.stderr.read())
        return
    # Literal grep equivalent for Windows hosts without ripgrep.
    count = 0
    for scope in SCOPES:
        for path in sorted((ROOT / scope).rglob("*")):
            if path.suffix not in (".py", ".json") or not path.is_file():
                continue
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if keyword in line:
                    print(f"{path.relative_to(ROOT)}:{number}:{line[:600]}")
                    count += 1
                    if count >= limit:
                        print("[output limited; narrow the keyword]")
                        return


def check():
    errors = []
    names = ["AGENTS.md", "docs/PROJECT_CONTEXT.md", "docs/REPO_MAP.md", "docs/ITERATION_ROADMAP.md"]
    for name in names:
        if not (ROOT / name).is_file():
            errors.append(f"missing {name}")
    if errors:
        print("\n".join(errors)); return 1
    roadmap = (ROOT / names[-1]).read_text(encoding="utf-8")
    dates = re.findall(r"^## (\d{4}-\d{2}-\d{2})", roadmap, re.M)
    if not dates or dates != sorted(dates, reverse=True):
        errors.append("iteration dates must be newest first")
    sections = roadmap.split("\n## ")
    if len(sections) < 2:
        print("iteration roadmap needs a dated entry")
        return 1
    latest = sections[1]
    for field in ("Branch:", "HEAD:", "PR:", "Validation:", "Next plan:", "Engineering:", "Domain:", "Release:"):
        if field not in latest:
            errors.append(f"latest iteration missing {field}")
    for value in (git("branch", "--show-current"), git("rev-parse", "HEAD")):
        if value not in latest:
            # A committed entry cannot contain its own commit hash. Accept only
            # an explicitly pinned publication parent of the current commit.
            parents = git("show", "-s", "--format=%P", "HEAD").split()
            pinned = re.search(r"remote publication parent `([0-9a-f]{40})`", latest)
            if len(value) == 40 and pinned and pinned.group(1) in parents:
                continue
            errors.append(f"latest iteration does not identify current revision: {value}")
    for name in names[1:]:
        path = ROOT / name
        for target in re.findall(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
            if "://" in target or target.startswith("#"):
                continue
            if not (path.parent / target.split("#")[0]).exists():
                errors.append(f"broken context link: {name} -> {target}")
    print("\n".join(errors) if errors else "Context bookkeeping OK; PR state, evidence freshness, legal authority and merge approval are NOT certified.")
    return int(bool(errors))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("brief")
    search = sub.add_parser("find")
    search.add_argument("keyword")
    search.add_argument("--limit", type=int, default=25, choices=range(1, 101), metavar="1..100")
    sub.add_parser("check")
    args = parser.parse_args()
    if args.command == "brief": brief()
    elif args.command == "find": find(args.keyword, args.limit)
    else: return check()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
