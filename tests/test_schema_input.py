"""Both input schemas are the runtime contract, not documentation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from iran_auto_claim.cli import main
from iran_auto_claim.engine import compute
from iran_auto_claim.fixtures import load_fixtures
from iran_auto_claim.review import Review
from iran_auto_claim.schema_input import (
    InputSchemaError,
    validate_claim,
    validate_review,
    validated_case,
)

REPO = Path(__file__).resolve().parents[1]
CASES = REPO / "cases"


def _domain(branch: str) -> str:
    if branch in ("THIRD_PARTY_FINANCIAL", "ARTICLE_8_NON_CONVENTIONAL", "ORDINARY_FINANCIAL"):
        return "THIRD_PARTY_FINANCIAL"
    if branch == "LEGAL_RECOVERY":
        return "LEGAL_RECOVERY"
    return "BODY"


def test_schema_shaped_examples_pass():
    for name in ("example_partial_resolved.json", "example_partial_unresolved.json"):
        validate_claim(json.loads((CASES / name).read_text(encoding="utf-8")))


def test_review_files_pass_and_only_authorized_emitted_cases_are_claims(kb):
    for path in sorted(CASES.glob("review_*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        validate_review(payload, kb)
        review = Review(payload, kb)
        if review.decision()["decision"] in ("COMPUTE", "SCENARIO_SET"):
            validate_claim(review.case_payload())


def test_fixture_payloads_pass_the_claim_schema():
    for fixture in load_fixtures():
        payload = {
                "claim_id": fixture["id"],
                "unit": fixture.get("unit", "million_toman"),
                "classification": {"branch": fixture["branch"], "domain": _domain(fixture["branch"])},
                "damage": fixture.get("inputs", {}),
            }
        for field in ("regulatory_snapshot", "vehicle", "event", "policy", "coverage_gate", "calculation_config"):
            if field in fixture:
                payload[field] = fixture[field]
        validate_claim(payload)


def test_unknown_field_missing_field_enum_and_boolean_have_stable_codes():
    with pytest.raises(InputSchemaError) as unknown:
        validate_claim({"claim_id": "X", "invented": 1})
    assert unknown.value.errors[0].code == "unknown_field"
    assert unknown.value.errors[0].path == "invented"

    with pytest.raises(InputSchemaError) as missing:
        validate_claim({"unit": "million_toman"})
    assert any(item.code == "missing_field" and item.path == "claim_id" for item in missing.value.errors)

    with pytest.raises(InputSchemaError) as enum_error:
        validate_claim({"claim_id": "X", "classification": {"branch": "NOT_A_BRANCH"}})
    assert enum_error.value.errors[0].code == "invalid_enum"

    with pytest.raises(InputSchemaError) as boolean_error:
        validate_claim({"claim_id": "X", "damage": {"gross": True}})
    assert boolean_error.value.errors[0].code == "invalid_boolean"
    assert boolean_error.value.errors[0].path == "damage.gross"


def test_a_boolean_string_is_not_accepted_as_a_boolean():
    with pytest.raises(InputSchemaError) as caught:
        validate_claim({"claim_id": "X", "damage": {"title_transferred": "false"}})
    assert caught.value.errors[0].code == "invalid_boolean"


def test_claim_numbers_do_not_accept_numeric_strings():
    with pytest.raises(InputSchemaError) as caught:
        validate_claim({"claim_id": "X", "damage": {"gross": "10"}})
    assert caught.value.errors[0].code == "invalid_type"
    assert caught.value.errors[0].path == "damage.gross"


@pytest.mark.parametrize(
    ("part", "path"),
    [
        ("not-an-object", "damage.parts[0]"),
        ({"category": "GLASS"}, "damage.parts[0].assessed_loss_irr"),
        ({}, "damage.replacement_parts[0].type"),
    ],
)
def test_malformed_parts_are_rejected_instead_of_skipped_or_defaulted(part, path):
    key = "replacement_parts" if part == {} else "parts"
    with pytest.raises(InputSchemaError) as caught:
        validate_claim({"claim_id": "X", "damage": {key: [part]}})
    assert any(item.path == path for item in caught.value.errors)


def test_false_and_zero_survive_validation_and_normalization():
    case = validated_case(
        {
            "claim_id": "X",
            "damage": {"gross": 0, "title_transferred": False},
        }
    )
    assert case.gross_damage == 0
    assert case.title_transferred is False


def test_itemised_depreciation_requires_sourced_event_and_production_years():
    payload = {
        "claim_id": "X",
        "classification": {"branch": "PARTIAL_DAMAGE"},
        "damage": {
            "parts": [{"category": "OTHER_REPLACEMENT_PART", "assessed_loss": 100}]
        },
    }
    with pytest.raises(InputSchemaError) as caught:
        validate_claim(payload)
    paths = {item.path for item in caught.value.errors if item.code == "missing_field"}
    assert {"regulatory_snapshot", "vehicle"} <= paths


def test_review_vocabularies_use_the_same_stable_errors(kb):
    with pytest.raises(InputSchemaError) as choice:
        validate_review({"claim_id": "X", "answers": {"Q-S2-01": "METEORITE"}}, kb)
    assert choice.value.errors[0].to_dict() == {
        "code": "invalid_enum",
        "path": "answers.Q-S2-01",
        "message": "answer is outside the closed set",
    }

    with pytest.raises(InputSchemaError) as evidence:
        validate_review(
            {"claim_id": "X", "answers": {"Q-S2-01": "UNKNOWN"}, "evidence_present": ["EVT_NOT_REAL"]},
            kb,
        )
    assert evidence.value.errors[0].code == "invalid_enum"
    assert evidence.value.errors[0].path == "evidence_present[0]"


def test_review_emits_every_previously_missing_case_field(kb):
    full = Review.from_file(CASES / "review_t1_fullcover_partial.json", kb).case_payload()
    assert full["coverage_gate"]["risk_intensified"] is False
    assert full["policy"]["multiple_insurance"] == {"state": "NO", "prior_compensation": 0}

    glass = Review.from_file(CASES / "review_t4_glass_terms_missing.json", kb).case_payload()
    assert glass["policy"]["glass_valuation_condition"] == "WORDING_NOT_OBTAINED"


def test_theft_without_a_type_is_rejected():
    with pytest.raises(InputSchemaError) as caught:
        validate_claim(
            {"claim_id": "X", "classification": {"branch": "THEFT"}, "damage": {"gross": 10}}
        )
    assert any(item.code == "missing_field" for item in caught.value.errors)


def test_review_schema_rejects_an_unknown_top_level_field():
    with pytest.raises(InputSchemaError) as caught:
        validate_review({"claim_id": "X", "answers": {"Q-S0-06": "IN_FORCE"}, "payable": 1})
    assert caught.value.errors[0].code == "unknown_field"
    assert caught.value.errors[0].path == "payable"


def test_public_calc_rejects_a_malformed_case(capsys, tmp_path):
    target = tmp_path / "bad.json"
    target.write_text(json.dumps({"claim_id": "X", "unit": "farsakh"}), encoding="utf-8")
    assert main(["calc", str(target)]) == 1
    body = json.loads(capsys.readouterr().out)
    assert body["ok"] is False
    assert body["errors"][0]["code"] == "invalid_enum"


@pytest.mark.parametrize("command", ["calc", "review"])
def test_cli_reports_malformed_json_with_a_stable_code(command, capsys, tmp_path):
    target = tmp_path / "broken.json"
    target.write_text('{"claim_id":', encoding="utf-8")
    assert main([command, str(target)]) == 1
    body = json.loads(capsys.readouterr().out)
    assert body["errors"][0]["code"] == "invalid_json"
    assert body["errors"][0]["path"] == "$"


def test_public_compute_rejects_before_arithmetic():
    with pytest.raises(InputSchemaError):
        compute({"claim_id": "X", "damage": {"not_a_loss_figure": 1}})
