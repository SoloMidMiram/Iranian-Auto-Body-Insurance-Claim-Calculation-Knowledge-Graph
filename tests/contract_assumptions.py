"""Explicit synthetic contracts for arithmetic-positive tests, never real authority."""
import copy

from iran_auto_claim.fixtures import _with_synthetic_authority
from iran_auto_claim.knowledge import Knowledge
from iran_auto_claim.review import Review


def with_review_contract(payload, kb=None):
    result = copy.deepcopy(payload)
    raw = Review(result, kb or Knowledge.load()).case_payload()
    raw.get("policy", {}).get("franchise", {}).pop("authority", None)
    compiled = _with_synthetic_authority(raw)
    policy = compiled["policy"]
    spec = policy.get("franchise") or {}
    if "authority" not in spec:
        raise ValueError("positive software control needs explicit synthetic franchise terms")
    result["contract_context"] = {k: policy[k] for k in (
        "insurer", "product", "policy_reference", "policy_date", "contract_kind")}
    result["answers"].setdefault("Q-S6-04", {})["authority"] = spec["authority"]
    return result
