#!/usr/bin/env python3
"""Validate the bilingual customer FAQ and keep its Markdown view current."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from iran_auto_claim.knowledge import Knowledge  # noqa: E402

DATA = ROOT / "knowledge" / "customer_faq.json"
DOC = ROOT / "docs" / "CUSTOMER_FAQ.md"
PRIORITIES = ("P0", "P1", "P2")
BODY_SCOPES = {"ALL", "PARTIAL_DAMAGE", "TOTAL_LOSS", "GLASS_ONLY", "THEFT"}


def load_faq(root: Path = ROOT) -> dict[str, Any]:
    return json.loads((root / "knowledge" / "customer_faq.json").read_text(encoding="utf-8"))


def _language_index(section: dict[str, Any]) -> tuple[list[str], list[str], dict[str, dict[str, Any]]]:
    category_ids: list[str] = []
    faq_ids: list[str] = []
    faqs: dict[str, dict[str, Any]] = {}
    for category in section.get("categories") or []:
        category_ids.append(str(category.get("category_id")))
        for faq in category.get("faqs") or []:
            faq_id = str(faq.get("faq_id"))
            faq_ids.append(faq_id)
            faqs[faq_id] = faq
    return category_ids, faq_ids, faqs


def validate_faq(data: dict[str, Any], kb: Knowledge) -> list[str]:
    issues: list[str] = []
    metadata = data.get("metadata") or {}
    expected_metadata = {
        "status": "RESEARCH_AND_ADJUSTER_DECISION_SUPPORT",
        "scope": "BODY_ONLY",
        "mode": "EXPLANATORY_ONLY",
        "may_bind_claim_parameters": False,
        "may_calculate": False,
    }
    for field, expected in expected_metadata.items():
        if metadata.get(field) != expected:
            issues.append(f"metadata.{field} must be {expected!r}")

    hierarchy = data.get("hierarchy") or []
    hierarchy_ids = [str(item.get("category_id")) for item in hierarchy]
    ranks = [item.get("rank") for item in hierarchy]
    if ranks != list(range(1, len(hierarchy) + 1)):
        issues.append("hierarchy ranks must be unique and contiguous from 1")
    if len(hierarchy_ids) != len(set(hierarchy_ids)):
        issues.append("hierarchy contains duplicate category ids")
    known_categories = set(hierarchy_ids)
    for item in hierarchy:
        if item.get("priority") not in PRIORITIES:
            issues.append(f"hierarchy {item.get('category_id')}: unknown priority")
        for dependency in item.get("depends_on") or []:
            if dependency not in known_categories:
                issues.append(f"hierarchy {item.get('category_id')}: unknown dependency {dependency}")

    indices: dict[str, tuple[list[str], list[str], dict[str, dict[str, Any]]]] = {}
    for language, expected_direction in (("english", "ltr"), ("persian", "rtl")):
        section = data.get(language) or {}
        if section.get("direction") != expected_direction:
            issues.append(f"{language}.direction must be {expected_direction}")
        categories = section.get("categories") or []
        category_ids, faq_ids, faqs = _language_index(section)
        indices[language] = (category_ids, faq_ids, faqs)
        if category_ids != hierarchy_ids:
            issues.append(f"{language}: categories must follow the declared hierarchy")
        if len(faq_ids) != len(set(faq_ids)):
            issues.append(f"{language}: duplicate faq ids")
        for category, hierarchy_item in zip(categories, hierarchy):
            category_id = category.get("category_id", "<missing>")
            if category.get("rank") != hierarchy_item.get("rank"):
                issues.append(f"{language} {category_id}: rank differs from hierarchy")
            if category.get("priority") != hierarchy_item.get("priority"):
                issues.append(f"{language} {category_id}: priority differs from hierarchy")
            orders = [faq.get("order") for faq in category.get("faqs") or []]
            if orders != list(range(1, len(orders) + 1)):
                issues.append(f"{language} {category_id}: FAQ order must be contiguous from 1")
            for faq in category.get("faqs") or []:
                faq_id = faq.get("faq_id", "<missing>")
                for field in ("question", "answer_summary", "answer", "customer_action"):
                    if not str(faq.get(field) or "").strip():
                        issues.append(f"{language} {faq_id}: missing {field}")
                if faq.get("priority") not in PRIORITIES:
                    issues.append(f"{language} {faq_id}: unknown priority")
                scopes = set(faq.get("applies_to") or [])
                if not scopes or not scopes <= BODY_SCOPES:
                    issues.append(f"{language} {faq_id}: invalid applies_to {sorted(scopes)}")
                refs = faq.get("knowledge_refs") or []
                if not refs:
                    issues.append(f"{language} {faq_id}: no knowledge_refs")
                for ref in refs:
                    if ref not in kb.all_ids:
                        issues.append(f"{language} {faq_id}: unknown knowledge ref {ref}")

    en_categories, en_ids, en_faqs = indices.get("english", ([], [], {}))
    fa_categories, fa_ids, fa_faqs = indices.get("persian", ([], [], {}))
    if en_categories != fa_categories:
        issues.append("English and Persian category ids/order differ")
    if en_ids != fa_ids:
        issues.append("English and Persian FAQ ids/order differ")
    for faq_id in en_ids:
        en = en_faqs[faq_id]
        fa = fa_faqs.get(faq_id) or {}
        for field in ("priority", "applies_to", "knowledge_refs"):
            if en.get(field) != fa.get(field):
                issues.append(f"{faq_id}: English/Persian {field} differs")

    return issues


def _render_language(title: str, section: dict[str, Any], *, rtl: bool) -> list[str]:
    lines = [f"## {title}", ""]
    if rtl:
        lines.extend(["<div dir=\"rtl\">", ""])
    for category in section["categories"]:
        lines.extend(
            [
                f"### {category['rank']}. {category['title']} — {category['priority']}",
                "",
                category["purpose"],
                "",
            ]
        )
        for faq in category["faqs"]:
            lines.extend(
                [
                    f"#### {faq['faq_id']} · {faq['priority']} · {faq['question']}",
                    "",
                    f"**{'پاسخ کوتاه' if rtl else 'Short answer'}:** {faq['answer_summary']}",
                    "",
                    faq["answer"],
                    "",
                    f"**{'اقدام بعدی مشتری' if rtl else 'Customer action'}:** {faq['customer_action']}",
                    "",
                    f"**{'پیوند به مدل دانش' if rtl else 'Knowledge-model links'}:** "
                    + ", ".join(f"`{item}`" for item in faq["knowledge_refs"]),
                    "",
                ]
            )
    if rtl:
        lines.extend(["</div>", ""])
    return lines


def render_faq(data: dict[str, Any]) -> str:
    lines = [
        "# Customer FAQ: Body-Claim Recognition and Calculation",
        "",
        "<!-- Generated by scripts/sync_customer_faq.py from knowledge/customer_faq.json. -->",
        "",
        "> This FAQ explains the model. It does not bind claim facts, authorize a",
        "> calculation, authenticate documents, or replace insurer/legal review.",
        "",
        "## Category hierarchy and priority",
        "",
        "`P0` categories should be read first, `P1` categories explain amounts and",
        "evidence, and `P2` categories explain follow-up and escalation.",
        "",
        "| Rank | Category | Priority | Depends on |",
        "|---:|---|---|---|",
    ]
    en_by_id = {item["category_id"]: item for item in data["english"]["categories"]}
    for item in data["hierarchy"]:
        category = en_by_id[item["category_id"]]
        dependencies = ", ".join(f"`{dep}`" for dep in item["depends_on"]) or "—"
        lines.append(
            f"| {item['rank']} | {category['title']} (`{item['category_id']}`) | "
            f"{item['priority']} | {dependencies} |"
        )
    lines.extend(
        [
            "",
            "```text",
            "Start and scope",
            "└─ Recognition",
            "   └─ Acceptance",
            "      ├─ Calculation",
            "      │  └─ Results, scenarios, and confidence",
            "      └─ Evidence and documents",
            "         └─ Next steps and review",
            "```",
            "",
        ]
    )
    lines.extend(_render_language("English FAQ", data["english"], rtl=False))
    lines.extend(_render_language("پرسش‌های متداول فارسی", data["persian"], rtl=True))
    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="rewrite docs/CUSTOMER_FAQ.md")
    parser.add_argument("--root", default=str(ROOT), help="repository root")
    args = parser.parse_args(argv)
    root = Path(args.root)
    data = load_faq(root)
    issues = validate_faq(data, Knowledge.load(root))
    if issues:
        print("customer FAQ validation failed:")
        for issue in issues:
            print(f"  - {issue}")
        return 1
    rendered = render_faq(data)
    doc = root / "docs" / "CUSTOMER_FAQ.md"
    if args.write:
        doc.write_text(rendered, encoding="utf-8")
        print(f"wrote {doc.relative_to(root)}")
        return 0
    if not doc.exists() or doc.read_text(encoding="utf-8") != rendered:
        print("customer FAQ documentation is stale; re-run with --write")
        return 1
    print("customer FAQ data and documentation are current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
