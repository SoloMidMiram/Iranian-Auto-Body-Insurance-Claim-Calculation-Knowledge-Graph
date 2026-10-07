"""Bilingual customer FAQ correspondence and knowledge-link integrity."""

from scripts.sync_customer_faq import load_faq, render_faq, validate_faq


def test_customer_faq_validates_against_the_knowledge_model(kb):
    assert validate_faq(load_faq(), kb) == []


def test_customer_faq_is_explanatory_only():
    metadata = load_faq()["metadata"]
    assert metadata["mode"] == "EXPLANATORY_ONLY"
    assert metadata["may_bind_claim_parameters"] is False
    assert metadata["may_calculate"] is False


def test_customer_faq_markdown_is_generated_from_json():
    data = load_faq()
    rendered = render_faq(data)
    with open("docs/CUSTOMER_FAQ.md", encoding="utf-8") as document:
        assert document.read() == rendered


def test_english_precedes_persian_and_ids_correspond():
    data = load_faq()
    rendered = render_faq(data)
    assert rendered.index("## English FAQ") < rendered.index("## پرسش‌های متداول فارسی")
    english_ids = [
        faq["faq_id"]
        for category in data["english"]["categories"]
        for faq in category["faqs"]
    ]
    persian_ids = [
        faq["faq_id"]
        for category in data["persian"]["categories"]
        for faq in category["faqs"]
    ]
    assert english_ids == persian_ids
