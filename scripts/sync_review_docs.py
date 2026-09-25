#!/usr/bin/env python
"""Rewrite the generated blocks inside docs/BODY_CASE_REVIEW_MODEL.md.

The document embeds the flowchart and the three reference tables so an adjuster can
read one file instead of running four commands. Embedded copies go stale the moment the
graph changes, so they are generated rather than maintained:

    python scripts/sync_review_docs.py            # report what is stale
    python scripts/sync_review_docs.py --write    # rewrite the blocks

`tests/test_review.py` asserts the same equality from the other direction, so a
hand-edited table inside a marker fails CI just as an un-synced document does.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from iran_auto_claim.knowledge import Knowledge  # noqa: E402
from iran_auto_claim.review import (  # noqa: E402
    ladder_markdown,
    mermaid_flowchart,
    parameters_markdown,
    questionnaire_markdown,
)

DOC = ROOT / "docs" / "BODY_CASE_REVIEW_MODEL.md"


def blocks(kb: Knowledge) -> dict[str, str]:
    return {
        "flowchart": mermaid_flowchart(kb),
        "questionnaire": questionnaire_markdown(kb),
        "parameters": parameters_markdown(kb),
        "ladder": ladder_markdown(kb),
        "promotion-rules": "\n".join(f"* {rule}" for rule in kb.tiers_raw["promotion_rule"]),
    }


def render(document: str, kb: Knowledge) -> tuple[str, list[str]]:
    stale: list[str] = []
    for name, body in blocks(kb).items():
        begin = f"<!-- BEGIN GENERATED: {name} -->"
        end = f"<!-- END GENERATED: {name} -->"
        if begin not in document or end not in document:
            stale.append(f"{name}: markers missing from the document")
            continue
        head, rest = document.split(begin, 1)
        _, tail = rest.split(end, 1)
        replacement = f"{begin}\n\n{body}\n\n{end}"
        if (head + replacement + tail) != document:
            stale.append(name)
        document = head + replacement + tail
    return document, stale


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="rewrite the generated blocks")
    parser.add_argument("--root", default=str(ROOT), help="repository root")
    args = parser.parse_args(argv)

    document = DOC.read_text(encoding="utf-8")
    rendered, stale = render(document, Knowledge.load(args.root))
    if not stale:
        print("documentation blocks are current")
        return 0
    if not args.write:
        print("stale generated block(s): " + ", ".join(stale))
        print("re-run with --write")
        return 1
    DOC.write_text(rendered, encoding="utf-8")
    print(f"rewrote {len(stale)} block(s) in {DOC.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
