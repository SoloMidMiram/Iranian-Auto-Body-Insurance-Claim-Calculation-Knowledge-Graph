"""Bilingual customer FAQ correspondence and knowledge-link integrity."""

import pytest

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


def test_customer_journey_and_questions_render_in_declared_order():
    data = load_faq()
    expected_categories = [
        "CAT-01_START_SCOPE",
        "CAT-06_EVIDENCE_DOCUMENTS",
        "CAT-02_RECOGNITION",
        "CAT-03_ACCEPTANCE",
        "CAT-04_CALCULATION",
        "CAT-05_RESULTS_UNCERTAINTY",
        "CAT-07_NEXT_STEPS",
    ]
    expected_questions = {
        "CAT-02_RECOGNITION": [
            "FAQ-RECOG-002",
            "FAQ-RECOG-001",
            "FAQ-RECOG-003",
            "FAQ-RECOG-004",
            "FAQ-RECOG-005",
        ],
        "CAT-03_ACCEPTANCE": [
            "FAQ-ACCEPT-001",
            "FAQ-ACCEPT-002",
            "FAQ-ACCEPT-005",
            "FAQ-ACCEPT-003",
            "FAQ-ACCEPT-004",
        ],
        "CAT-04_CALCULATION": [
            "FAQ-CALC-001",
            "FAQ-CALC-004",
            "FAQ-CALC-002",
            "FAQ-CALC-003",
            "FAQ-CALC-005",
            "FAQ-CALC-006",
        ],
        "CAT-05_RESULTS_UNCERTAINTY": [
            "FAQ-RESULT-004",
            "FAQ-RESULT-002",
            "FAQ-RESULT-003",
            "FAQ-RESULT-005",
            "FAQ-RESULT-001",
        ],
    }
    for language in ("english", "persian"):
        categories = sorted(data[language]["categories"], key=lambda item: item["rank"])
        assert [item["category_id"] for item in categories] == expected_categories
        for category in categories:
            expected = expected_questions.get(category["category_id"])
            if expected:
                faqs = sorted(category["faqs"], key=lambda item: item["order"])
                assert [item["faq_id"] for item in faqs] == expected


def test_customer_faq_rejects_duplicate_json_keys(tmp_path):
    knowledge = tmp_path / "knowledge"
    knowledge.mkdir()
    (knowledge / "customer_faq.json").write_text('{"version": 1, "version": 2}', encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate JSON key: version"):
        load_faq(tmp_path)
