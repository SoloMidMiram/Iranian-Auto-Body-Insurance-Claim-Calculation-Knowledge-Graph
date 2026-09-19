"""The P01-L50 corpus is the contract: every fixture must pass."""

from __future__ import annotations

import pytest

from iran_auto_claim.fixtures import evaluate_fixture, load_fixtures

FIXTURES = load_fixtures()
IDS = [fixture["id"] for fixture in FIXTURES]


def test_corpus_size():
    assert len(FIXTURES) == 50


def test_fixture_ids_are_unique():
    assert len(IDS) == len(set(IDS))


def test_every_fixture_asserts_something():
    empty = [fixture["id"] for fixture in FIXTURES if not fixture.get("expected")]
    assert empty == [], f"fixtures with no expectation would pass vacuously: {empty}"


@pytest.mark.parametrize("fixture", FIXTURES, ids=IDS)
def test_fixture(fixture, kb):
    _, problems = evaluate_fixture(fixture, kb)
    assert problems == [], "; ".join(problems)


def test_expected_keys_are_within_the_supported_vocabulary(kb):
    """An expectation the harness cannot resolve must fail, not be ignored."""
    from iran_auto_claim.fixtures import EXACT_ATTR_KEYS, LABEL_KEYS, PAYABLE_KEYS, SCENARIO_KEYS

    known = PAYABLE_KEYS | set(SCENARIO_KEYS) | LABEL_KEYS | set(EXACT_ATTR_KEYS)
    unknown = set()
    for fixture in FIXTURES:
        for key in fixture["expected"]:
            if key in known:
                continue
            # otherwise the key must be a field the engine actually produces
            _, problems = evaluate_fixture(fixture, kb)
            if any(problem.startswith(f"{key}: UNRESOLVED") for problem in problems):
                unknown.add(key)
    assert unknown == set(), f"expectation keys with no engine field: {sorted(unknown)}"


@pytest.mark.parametrize("fixture_id", IDS)
def test_fixture_result_is_json_serialisable(fixture_id, kb):
    import json

    fixture = next(item for item in FIXTURES if item["id"] == fixture_id)
    result, _ = evaluate_fixture(fixture, kb)
    json.dumps(result.to_dict())
