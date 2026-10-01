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


def test_review_files_and_their_emitted_cases_pass(kb):
    for path in sorted(CASES.glob("review_*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        validate_review(payload)
        emitted = Review(payload, kb).case_payload()
        validate_claim(emitted)


def test_fixture_payloads_pass_the_claim_schema():
    for fixture in load_fixtures():
        validate_claim(
            {
                "claim_id": fixture["id"],
                "unit": fixture.get("unit", "million_toman"),
                "classification": {"branch": fixture["branch"], "domain": _domain(fixture["branch"])},
                "damage": fixture.get("inputs", {}),
            }
        )


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


def test_public_compute_rejects_before_arithmetic():
    with pytest.raises(InputSchemaError):
        compute({"claim_id": "X", "damage": {"not_a_loss_figure": 1}})
