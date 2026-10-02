"""Provenance names the chain separately from formula confidence."""

from __future__ import annotations

from iran_auto_claim.engine import compute
from iran_auto_claim.money import D


def _partial(gross: int = 1600, franchise: int = 100) -> dict:
    return {
        "claim_id": "prov",
        "unit": "IRR",
        "classification": {"branch": "PARTIAL_DAMAGE", "domain": "BODY"},
        "event": {"event_date": "1405/06/01"},
        "damage": {"gross": gross},
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
