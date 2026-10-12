"""Both input schemas are the runtime contract, not documentation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from iran_auto_claim.admission import AuthorizationError
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
                "unit": fixture.get("unit", "IRR"),
                "classification": {"branch": fixture["branch"], "domain": _domain(fixture["branch"])},
                "damage": fixture.get("inputs", {}),
            }
        for field in ("regulatory_snapshot", "vehicle", "event", "policy", "coverage_gate", "calculation_config"):
            if field in fixture:
                payload[field] = fixture[field]
        validate_claim(payload)


def test_unknown_field_missing_field_enum_and_boolean_have_stable_codes():
    with pytest.raises(InputSchemaError) as unknown:
        validate_claim({"claim_id": "X", "unit": "IRR", "invented": 1})
    assert unknown.value.errors[0].code == "unknown_field"
    assert unknown.value.errors[0].path == "invented"

    with pytest.raises(InputSchemaError) as missing:
        validate_claim({"unit": "IRR"})
    assert any(item.code == "missing_field" and item.path == "claim_id" for item in missing.value.errors)

    with pytest.raises(InputSchemaError) as enum_error:
        validate_claim({"claim_id": "X", "unit": "IRR", "classification": {"branch": "NOT_A_BRANCH"}})
    assert enum_error.value.errors[0].code == "invalid_enum"

    with pytest.raises(InputSchemaError) as boolean_error:
        validate_claim({"claim_id": "X", "unit": "IRR", "damage": {"gross": True}})
    assert boolean_error.value.errors[0].code == "invalid_boolean"
    assert boolean_error.value.errors[0].path == "damage.gross"


def test_a_boolean_string_is_not_accepted_as_a_boolean():
    with pytest.raises(InputSchemaError) as caught:
        validate_claim({"claim_id": "X", "unit": "IRR", "damage": {"title_transferred": "false"}})
    assert caught.value.errors[0].code == "invalid_boolean"


def test_claim_numbers_do_not_accept_numeric_strings():
    with pytest.raises(InputSchemaError) as caught:
        validate_claim({"claim_id": "X", "unit": "IRR", "damage": {"gross": "10"}})
    assert caught.value.errors[0].code == "invalid_type"
    assert caught.value.errors[0].path == "damage.gross"


@pytest.mark.parametrize("amount", [-1, 1.5, float("nan"), float("inf"), -float("inf")])
def test_claim_money_must_be_non_negative_integer_irr(amount):
    with pytest.raises(InputSchemaError) as caught:
        validate_claim({"claim_id": "X", "unit": "IRR", "damage": {"gross": amount}})
    assert caught.value.errors[0].code == "invalid_type"
    assert caught.value.errors[0].path == "damage.gross"


@pytest.mark.parametrize("unit", ["toman", "million_toman", "billion_toman", "irr"])
def test_display_units_cannot_cross_the_claim_boundary(unit):
    with pytest.raises(InputSchemaError) as caught:
        validate_claim({"claim_id": "X", "unit": unit, "damage": {"gross": 10}})
    assert caught.value.errors[0].code == "invalid_enum"
    assert caught.value.errors[0].path == "unit"


def test_review_money_rejects_fractional_irr_and_numeric_strings(kb):
    for value in (1.5, "100"):
        with pytest.raises(InputSchemaError) as caught:
            validate_review(
                {"claim_id": "X", "unit": "IRR", "answers": {"Q-S4-02": value}}, kb
            )
        assert caught.value.errors[0].code == "invalid_type"
        assert caught.value.errors[0].path == "answers.Q-S4-02"


@pytest.mark.parametrize(
    "value",
    ["1404-99-99", "1404-12-30", "2025-02-29", "1501-01-01"],
)
def test_event_dates_reject_impossible_or_calendar_ambiguous_values(value):
    with pytest.raises(InputSchemaError) as caught:
        validate_claim(
            {"claim_id": "X", "unit": "IRR", "event": {"event_date": value}}
        )
    assert caught.value.errors[0].code == "invalid_date"
    assert caught.value.errors[0].path == "event.event_date"


@pytest.mark.parametrize(
    "value",
    ["1403-12-30", "1403/12/30", "2024-02-29"],
)
def test_supported_shamsi_and_gregorian_date_spellings_are_valid(value):
    validate_claim(
        {"claim_id": "X", "unit": "IRR", "event": {"event_date": value}}
    )


def test_review_dates_use_the_same_calendar_contract(kb):
    with pytest.raises(InputSchemaError) as caught:
        validate_review(
            {
                "claim_id": "X",
                "unit": "IRR",
                "answers": {"Q-S0-02": "1404-12-30"},
            },
            kb,
        )
    assert caught.value.errors[0].to_dict() == {
        "code": "invalid_date",
        "path": "answers.Q-S0-02",
        "message": "invalid Shamsi day",
    }


def test_event_chronology_uses_field_specific_predicates(kb):
    payload = {
        "claim_id": "X",
        "unit": "IRR",
        "answers": {
            "Q-S0-02": "1404-02-02",
            "Q-S0-03": "1404-02-01",
            "Q-S0-07": "1404-01-31",
        },
    }
    with pytest.raises(InputSchemaError) as caught:
        validate_review(payload, kb)
    errors = {(item.code, item.path) for item in caught.value.errors}
    assert ("invalid_chronology", "answers.Q-S0-03") in errors
    assert ("invalid_chronology", "answers.Q-S0-07") in errors


def test_claim_chronology_applies_only_to_the_canonical_claim_sequence():
    same_day = {
        "claim_id": "X",
        "unit": "IRR",
        "regulatory_snapshot": {"as_of_date": "2020-01-01"},
        "classification": {
            "override": {
                "authorized": True,
                "actor": "reviewer",
                "reason": "chronology control",
                "source": "test record",
                "timestamp": "2019-01-01T00:00:00Z",
            }
        },
        "event": {
            "event_date": "1404-02-01",
            "awareness_date": "1404-02-01",
            "declaration_date": "1404-02-01",
        },
    }
    # Evaluation and override provenance can predate the represented event in a
    # synthetic file; PR-01 validates their own formats but does not make them a
    # legal clock or part of the insured's event/awareness/declaration sequence.
    validate_claim(same_day)

    declaration_before_awareness = {
        "claim_id": "X",
        "unit": "IRR",
        "event": {
            "awareness_date": "1404-02-02",
            "declaration_date": "1404-02-01",
        },
    }
    with pytest.raises(InputSchemaError) as caught:
        validate_claim(declaration_before_awareness)
    assert caught.value.errors[0].to_dict() == {
        "code": "invalid_chronology",
        "path": "event.declaration_date",
        "message": "declaration date precedes awareness of the loss",
    }


def test_gregorian_occurrence_without_supported_shamsi_mapping_refuses_cleanly():
    with pytest.raises(InputSchemaError) as caught:
        validate_claim(
            {
                "claim_id": "X",
                "unit": "IRR",
                "event": {"event_date": "9999-12-31"},
            }
        )
    assert caught.value.errors[0].code == "invalid_date"
    assert caught.value.errors[0].path == "event.event_date"


def test_event_year_and_production_year_must_reconcile():
    payload = {
        "claim_id": "X",
        "unit": "IRR",
        "regulatory_snapshot": {"iranian_year": 1404},
        "vehicle": {"production_year_shamsi": 1406},
        "event": {"event_date": "2026-03-21"},
    }
    with pytest.raises(InputSchemaError) as caught:
        validate_claim(payload)
    errors = {(item.code, item.path) for item in caught.value.errors}
    # 2026-03-21 is 1405-01-01, so both the supplied claim year and the
    # production/event ordering are checked against the converted event fact.
    assert ("conflicting_year", "regulatory_snapshot.iranian_year") in errors
    assert ("invalid_chronology", "vehicle.production_year_shamsi") in errors


def test_equal_true_aliases_pass_and_unequal_true_aliases_reject():
    equal = {
        "claim_id": "X",
        "unit": "IRR",
        "regulatory_snapshot": {"iranian_year": 1405},
        "vehicle": {"production_year_shamsi": 1405},
        "damage": {
            "parts": [
                {
                    "category": "OTHER_REPLACEMENT_PART",
                    "assessed_loss": 100,
                    "assessed_loss_irr": 100,
                }
            ]
        },
    }
    case = validated_case(equal)
    assert case.parts == [
        {
            "name": None,
            "category": "OTHER_REPLACEMENT_PART",
            "assessed_loss": 100,
            "new_price": None,
            "requires_replacement": True,
        }
    ]
    equal["damage"]["parts"][0]["assessed_loss_irr"] = 99
    with pytest.raises(InputSchemaError) as caught:
        validate_claim(equal)
    assert caught.value.errors[0].code == "conflicting_alias"
    assert caught.value.errors[0].path == "damage.parts[0].assessed_loss_irr"


def test_distinct_money_operands_and_contractual_carriers_are_not_aliases():
    validate_claim(
        {
            "claim_id": "X",
            "unit": "IRR",
            "regulatory_snapshot": {
                "iranian_year": 1405,
                "conventional_vehicle_threshold_irr": 1400,
            },
            "vehicle": {"market_value_at_event_irr": 2000},
            "damage": {
                "rescue_transport_actual_irr": 100,
                "rescue_payable": 80,
                "rescue_for_total_loss_test_irr": 50,
                "victim_vehicle_value": 1000,
                "conventional_threshold": 1500,
                "franchise": 10,
            },
            "policy": {
                "franchise": {
                    "mode": "ABSOLUTE",
                    "absolute_irr": 20,
                    "source": "POLICY",
                }
            },
        }
    )


def test_repair_only_status_defaults_false_and_contradictions_reject():
    payload = {
        "claim_id": "X",
        "unit": "IRR",
        "regulatory_snapshot": {"iranian_year": 1405},
        "vehicle": {"production_year_shamsi": 1400},
        "damage": {"parts": [{"category": "REPAIR_ONLY", "assessed_loss": 100}]},
    }
    assert validated_case(payload).parts[0]["requires_replacement"] is False

    payload["damage"]["parts"][0]["requires_replacement"] = True
    with pytest.raises(InputSchemaError) as caught:
        validate_claim(payload)
    assert any(
        issue.code == "contradictory_input"
        and issue.path == "damage.parts[0].requires_replacement"
        for issue in caught.value.errors
    )

    payload["damage"] = {
        "replacement_parts": [{"type": "REPAIR_ONLY", "loss": 100}]
    }
    with pytest.raises(InputSchemaError) as caught:
        validate_claim(payload)
    assert any(
        issue.code == "contradictory_input"
        and issue.path == "damage.replacement_parts[0].type"
        for issue in caught.value.errors
    )

    payload["damage"] = {
        "replacement_parts": [{"category": "REPAIR_ONLY", "loss": 100}]
    }
    with pytest.raises(InputSchemaError) as caught:
        validate_claim(payload)
    assert any(
        issue.code == "contradictory_input"
        and issue.path == "damage.replacement_parts[0].category"
        for issue in caught.value.errors
    )


@pytest.mark.parametrize(
    "actual_rescue",
    [None, 100],
    ids=("missing-actual", "mismatched-actual"),
)
def test_derived_classification_rescue_requires_matching_actual_expense(actual_rescue):
    damage = {
        "rescue_for_total_loss_test_irr": 101,
        "rescue_for_total_loss_test_source": "DERIVED_FROM_ACTUAL_RESCUE",
    }
    if actual_rescue is not None:
        damage["rescue_transport_actual_irr"] = actual_rescue
    payload = {"claim_id": "X", "unit": "IRR", "damage": damage}

    with pytest.raises(InputSchemaError) as caught:
        validate_claim(payload)

    assert any(
        issue.code == "contradictory_input"
        and issue.path == "damage.rescue_for_total_loss_test_source"
        for issue in caught.value.errors
    )


def test_derived_classification_rescue_accepts_matching_actual_expense():
    validate_claim(
        {
            "claim_id": "X",
            "unit": "IRR",
            "damage": {
                "rescue_transport_actual_irr": 101,
                "rescue_for_total_loss_test_irr": 101,
                "rescue_for_total_loss_test_source": "DERIVED_FROM_ACTUAL_RESCUE",
            },
        }
    )


@pytest.mark.parametrize(
    "actual_rescue",
    [None, 101],
    ids=("without-actual", "with-incidental-actual"),
)
def test_explicit_classification_rescue_source_requires_threshold_operand(
    actual_rescue,
):
    damage = {
        "rescue_for_total_loss_test_source": "EXPLICIT_THRESHOLD_OPERAND",
    }
    if actual_rescue is not None:
        damage["rescue_transport_actual_irr"] = actual_rescue
    payload = {"claim_id": "X", "unit": "IRR", "damage": damage}

    with pytest.raises(InputSchemaError) as caught:
        validate_claim(payload)

    assert any(
        issue.code == "contradictory_input"
        and issue.path == "damage.rescue_for_total_loss_test_source"
        for issue in caught.value.errors
    )


def test_explicit_classification_rescue_source_accepts_threshold_operand():
    validate_claim(
        {
            "claim_id": "X",
            "unit": "IRR",
            "damage": {
                "rescue_for_total_loss_test_irr": 101,
                "rescue_for_total_loss_test_source": "EXPLICIT_THRESHOLD_OPERAND",
            },
        }
    )


def test_review_rejects_repair_only_marked_as_replacement(kb):
    payload = {
        "claim_id": "X",
        "unit": "IRR",
        "answers": {
            "Q-S4-03": [
                {
                    "category": "REPAIR_ONLY",
                    "assessed_loss": 100,
                    "requires_replacement": True,
                }
            ]
        },
    }
    with pytest.raises(InputSchemaError) as caught:
        validate_review(payload, kb)
    assert any(issue.code == "contradictory_input" for issue in caught.value.errors)


def test_review_part_new_price_aliases_must_agree(kb):
    payload = {
        "claim_id": "X",
        "unit": "IRR",
        "answers": {
            "Q-S4-03": [
                {
                    "category": "BATTERY",
                    "assessed_loss": 100,
                    "new_price": 200,
                    "new_price_irr": 201,
                }
            ]
        },
    }
    with pytest.raises(InputSchemaError) as caught:
        validate_review(payload, kb)
    assert any(
        item.code == "conflicting_alias"
        and item.path == "answers.Q-S4-03[0].new_price_irr"
        for item in caught.value.errors
    )


@pytest.mark.parametrize("malformed", [[], {}], ids=("list", "object"))
def test_malformed_review_money_aliases_return_structured_errors(kb, malformed):
    payload = {
        "claim_id": "X",
        "unit": "IRR",
        "answers": {
            "Q-S4-03": [
                {
                    "category": "BATTERY",
                    "assessed_loss": malformed,
                    "assessed_loss_irr": 100,
                }
            ]
        },
    }
    with pytest.raises(InputSchemaError) as caught:
        validate_review(payload, kb)
    assert any(
        item.code == "invalid_type"
        and item.path == "answers.Q-S4-03[0].assessed_loss"
        for item in caught.value.errors
    )


@pytest.mark.parametrize("malformed", [[], {}], ids=("list", "object"))
def test_malformed_claim_money_aliases_return_structured_errors(malformed):
    with pytest.raises(InputSchemaError) as caught:
        validate_claim(
            {
                "claim_id": "X",
                "unit": "IRR",
                "damage": {"gross": malformed, "gross_damage_irr": 100},
            }
        )
    assert any(
        item.code == "invalid_type" and item.path == "damage.gross"
        for item in caught.value.errors
    )


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
        validate_claim({"claim_id": "X", "unit": "IRR", "damage": {key: [part]}})
    assert any(item.path == path for item in caught.value.errors)


def test_false_and_zero_survive_validation_and_normalization():
    case = validated_case(
        {
            "claim_id": "X",
            "unit": "IRR",
            "damage": {"gross": 0, "title_transferred": False},
        }
    )
    assert case.gross_damage == 0
    assert case.title_transferred is False


def test_itemised_depreciation_requires_sourced_event_and_production_years():
    payload = {
        "claim_id": "X",
        "unit": "IRR",
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
        validate_review({"claim_id": "X", "unit": "IRR", "answers": {"Q-S2-01": "METEORITE"}}, kb)
    assert choice.value.errors[0].to_dict() == {
        "code": "invalid_enum",
        "path": "answers.Q-S2-01",
        "message": "answer is outside the closed set",
    }

    with pytest.raises(InputSchemaError) as evidence:
        validate_review(
            {"claim_id": "X", "unit": "IRR", "answers": {"Q-S2-01": "UNKNOWN"}, "evidence_present": ["EVT_NOT_REAL"]},
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


@pytest.mark.parametrize("missing", ["state", "prior_compensation"])
def test_multiple_insurance_object_requires_both_distinct_facts(missing):
    multiple_insurance = {"state": "NO", "prior_compensation": 0}
    multiple_insurance.pop(missing)

    with pytest.raises(InputSchemaError) as caught:
        validate_claim(
            {
                "claim_id": "X",
                "unit": "IRR",
                "policy": {"multiple_insurance": multiple_insurance},
            }
        )

    assert any(
        item.code == "missing_field"
        and item.path == f"policy.multiple_insurance.{missing}"
        for item in caught.value.errors
    )


def test_theft_without_a_type_is_rejected():
    with pytest.raises(InputSchemaError) as caught:
        validate_claim(
            {"claim_id": "X", "unit": "IRR", "classification": {"branch": "THEFT"}, "damage": {"gross": 10}}
        )
    assert any(item.code == "missing_field" for item in caught.value.errors)


def test_review_schema_rejects_an_unknown_top_level_field():
    with pytest.raises(InputSchemaError) as caught:
        validate_review({"claim_id": "X", "unit": "IRR", "answers": {"Q-S0-06": "IN_FORCE"}, "payable": 1})
    assert caught.value.errors[0].code == "unknown_field"
    assert caught.value.errors[0].path == "payable"


def test_classification_override_requires_actor_reason_source_and_time():
    payload = {
        "claim_id": "X",
        "unit": "IRR",
        "classification": {
            "branch": "TOTAL_LOSS",
            "override": {"authorized": True, "actor": "reviewer"},
        },
    }
    with pytest.raises(InputSchemaError) as caught:
        validate_claim(payload)
    missing = {item.path for item in caught.value.errors if item.code == "missing_field"}
    assert {
        "classification.override.reason",
        "classification.override.source",
        "classification.override.timestamp",
    } <= missing


def test_public_calc_rejects_a_malformed_case(capsys, tmp_path):
    target = tmp_path / "bad.json"
    target.write_text(json.dumps({"claim_id": "X", "unit": "farsakh"}), encoding="utf-8")
    assert main(["calc", str(target)]) == 1
    body = json.loads(capsys.readouterr().out)
    assert body["ok"] is False
    assert any(
        item["code"] == "invalid_enum" and item["path"] == "unit"
        for item in body["errors"]
    )


@pytest.mark.parametrize("command", ["calc", "review"])
def test_cli_reports_malformed_json_with_a_stable_code(command, capsys, tmp_path):
    target = tmp_path / "broken.json"
    target.write_text('{"claim_id":', encoding="utf-8")
    assert main([command, str(target)]) == 1
    body = json.loads(capsys.readouterr().out)
    assert body["errors"][0]["code"] == "invalid_json"
    assert body["errors"][0]["path"] == "$"


def test_a_raw_claim_cannot_reach_compute_without_authorization():
    """The boundary: no authorization object, no calculation - not even a refusal result."""
    raw = {"claim_id": "X", "unit": "IRR", "damage": {"not_a_loss_figure": 1}}
    with pytest.raises(AuthorizationError):
        compute(raw)  # a dict is not a CalculationAuthorization
