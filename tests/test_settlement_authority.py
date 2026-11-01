"""Authority identity regressions; applicability is a separate required layer."""
import copy
import json
from pathlib import Path

import pytest

from iran_auto_claim.admission import _internal_test_direct_authorize
from iran_auto_claim.engine import compute
from iran_auto_claim.review import Review


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("source", ["POLICY", "ENDORSEMENT", "INSURER_MANUAL"])
@pytest.mark.parametrize("amount", [0, 100])
@pytest.mark.parametrize("field,value", [("source_reference", None), ("source_version", None), ("source_reference", " "), ("source_version", " ")])
def test_review_and_engine_refuse_unidentifiable_franchise(kb, source, amount, field, value):
    payload = json.loads((ROOT / "cases/review_t1_fullcover_partial.json").read_text(encoding="utf-8"))
    payload["answers"]["Q-S6-01"] = "ABSOLUTE"
    for question in ("Q-S6-02", "Q-S6-03", "Q-S6-04"):
        spec = {"mode": "ABSOLUTE", "absolute_irr": amount, "source": source,
                "source_reference": "SYNTHETIC contract clause", "source_version": "TEST-v1"}
        if value is None:
            spec.pop(field)
        else:
            spec[field] = value
        payload["answers"][question] = spec
    review = Review(payload, kb)
    assert review.decision()["decision"] == "INSUFFICIENT_INFORMATION"
    assert "U02_FRANCHISE_BASE_SCHEDULES" in review.open_uncertainties()
    assert review.calculate() is None
    raw = copy.deepcopy(review.case_payload())
    result = compute(_internal_test_direct_authorize(raw, purpose="S09_IDENTITY_COUNTEREXAMPLE"), kb)
    assert result.payable is None
    assert result.status == "FRANCHISE_AUTHORITY_REQUIRED"
    assert "U02_FRANCHISE_BASE_SCHEDULES" in result.blocking_uncertainties
