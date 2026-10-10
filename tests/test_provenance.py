"""Provenance names the chain separately from formula confidence."""

from __future__ import annotations

import pytest
from admission_shim import compute

from iran_auto_claim.money import D


def _partial(gross: int = 1600, franchise: int = 100) -> dict:
    return {
        "claim_id": "prov",
        "unit": "IRR",
        "classification": {"branch": "PARTIAL_DAMAGE", "domain": "BODY"},
        "event": {"event_date": "1405/06/01"},
        "damage": {"gross": gross, "depreciation": 0, "market": 2000, "insured": 2000},
        "policy": {
            "policy_version": "TEST-v1",
            "franchise": {
                "mode": "ABSOLUTE",
                "absolute_irr": franchise,
                "source": "POLICY",
                "source_reference": "test policy schedule",
                "source_version": "TEST-v1",
            },
        },
    }


def test_body_result_traces_source_rule_operator_execution_and_result(kb):
    result = compute(_partial(), kb)
    assert result.payable == D(1500)
    assert result.formula_confidence is not None
    assert result.evidence_confidence is None
    assert result.fields["provenance_findings"]
    assert result.provenance
    entry = next(
        item
        for item in result.provenance
        if item["rule"] == "REG53_POLICY_DEFINED_FRANCHISE"
    )
    assert entry["source"]
    assert "OP_FRANCHISE" in entry["operator"]
    assert entry["execution"]["snapshot_id"] == "BODY@1405/06/01"
    assert entry["execution"]["plan"]
    assert entry["result"] == D(1500)
    assert result.formula_confidence != result.evidence_confidence


def _required_evidence_first_definition(kb) -> list[str]:
    return list(kb.branch("PARTIAL_DAMAGE")["required_evidence"])


@pytest.mark.parametrize(
    ("evidence", "expect_missing"),
    [
        ({}, True),
        ("all_false", True),
        ("mixed", True),
        ("all_true", False),
    ],
)
def test_evidence_confidence_counts_boolean_values_not_key_presence_first_definition(
    kb, evidence, expect_missing
):
    required = _required_evidence_first_definition(kb)
    if evidence == "all_false":
        evidence_map = {item: False for item in required}
    elif evidence == "mixed":
        evidence_map = {item: False for item in required}
        evidence_map[required[0]] = True
    elif evidence == "all_true":
        evidence_map = {item: True for item in required}
    else:
        evidence_map = evidence

    payload = _partial()
    payload["evidence"] = evidence_map
    result = compute(payload, kb)

    assert result.payable == D(1500)
    findings = result.fields.get("provenance_findings") or []
    if expect_missing:
        assert result.evidence_confidence is None
        assert any("evidence missing" in finding for finding in findings)
    else:
        assert result.evidence_confidence == 1.0
        assert not any("evidence missing" in finding for finding in findings)


def _required_evidence_second_definition(kb) -> list[str]:
    return list(kb.branch("PARTIAL_DAMAGE")["required_evidence"])


@pytest.mark.parametrize(
    ("evidence", "expect_missing"),
    [
        ({}, True),
        ("all_false", True),
        ("mixed", True),
        ("all_true", False),
    ],
)
def test_evidence_confidence_counts_boolean_values_not_key_presence_second_definition(
    kb, evidence, expect_missing
):
    required = _required_evidence_second_definition(kb)
    if evidence == "all_false":
        evidence_map = {item: False for item in required}
    elif evidence == "mixed":
        evidence_map = {item: False for item in required}
        evidence_map[required[0]] = True
    elif evidence == "all_true":
        evidence_map = {item: True for item in required}
    else:
        evidence_map = evidence

    payload = _partial()
    payload["evidence"] = evidence_map
    result = compute(payload, kb)

    assert result.payable == D(1500)
    findings = result.fields.get("provenance_findings") or []
    if expect_missing:
        assert result.evidence_confidence is None
        assert any("evidence missing" in finding for finding in findings)
    else:
        assert result.evidence_confidence == 1.0
        assert not any("evidence missing" in finding for finding in findings)
