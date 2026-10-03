"""Calculation admission boundary.

The calculation engine may only run on a claim that some issuer has authorized.
This module owns that contract:

    raw claim -> review gate -> CalculationAuthorization -> compute()

Two producers exist, and both are explicit:

* ``Review.authorize()`` is the producer for claim files. It refuses to issue
  authorization for REFUSE and INSUFFICIENT_INFORMATION decisions, so those
  outcomes can never reach the calculator.
* ``engine_direct_authorize()`` is a narrow, named channel for the synthetic
  fixture corpus, the mutation probe, and direct CLI calculation. It performs
  schema validation only and records ``ENGINE_DIRECT`` as the issuer, so every
  result states which boundary admitted it.

The authorization binds the exact validated payload by content hash. A case
edited after authorization no longer matches its hash and ``compute()``
refuses it, which makes "authorize once, calculate something else" impossible.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .case import Case
from .schema_input import validated_case

ISSUER_REVIEW = "REVIEW_GATE"
ISSUER_ENGINE_DIRECT = "ENGINE_DIRECT"

#: The only review decisions that permit calculation. REFUSE and
#: INSUFFICIENT_INFORMATION are terminal and cannot be converted into an
#: authorization by any producer.
AUTHORIZED_DECISIONS = frozenset({"COMPUTE", "SCENARIO_SET"})


class AuthorizationError(TypeError):
    """The engine was asked to run without a valid authorization."""


class AuthorizationNotGranted(AuthorizationError):
    """A producer refused to issue authorization (REFUSE / INSUFFICIENT)."""


def claim_hash(payload: dict[str, Any]) -> str:
    """Content hash of a claim payload in canonical form.

    Sorted keys and compact separators make the hash stable across insertion
    order; ``default=str`` keeps Decimal-valued payloads hashable without
    changing their comparison semantics.
    """
    canonical = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class CalculationAuthorization:
    """Proof that one issuer admitted one exact claim payload for calculation.

    Attributes:
        case: the validated ``Case`` the engine must run on.
        decision: the issuing decision (``COMPUTE`` or ``SCENARIO_SET``).
        claim_hash: content hash of ``case.raw`` at issuance time.
        issuer: which producer issued this authorization.
        issued_at: UTC timestamp for review-issued authorizations.
        provenance: issuer-specific record (tier, live uncertainties, graph
            plan identity, ...) preserved into the calculation result.
    """

    case: Case
    decision: str
    claim_hash: str
    issuer: str
    issued_at: str | None = None
    provenance: dict[str, Any] = field(default_factory=dict)

    def verify(self) -> None:
        """Fail closed unless the decision authorizes and the payload matches."""
        if self.decision not in AUTHORIZED_DECISIONS:
            raise AuthorizationError(
                f"decision {self.decision!r} does not authorize calculation; "
                f"only {', '.join(sorted(AUTHORIZED_DECISIONS))} may"
            )
        if claim_hash(self.case.raw) != self.claim_hash:
            raise AuthorizationError(
                "claim payload no longer matches its authorization hash; "
                "re-run the review gate to authorize the edited case"
            )

    def provenance_record(self) -> dict[str, Any]:
        """The authorization provenance stamped onto every calculation result."""
        record: dict[str, Any] = {
            "issuer": self.issuer,
            "decision": self.decision,
            "claim_hash": self.claim_hash,
            "issued_at": self.issued_at,
        }
        record.update(self.provenance)
        return record


def engine_direct_authorize(
    case: Case | dict[str, Any],
    kb: Any | None = None,
) -> CalculationAuthorization:
    """Authorize a case through the narrow direct channel.

    For the synthetic fixture corpus, the mutation probe, property tests, and
    direct CLI calculation, where no review questionnaire exists. The schema
    boundary still runs; the issuer is recorded as ``ENGINE_DIRECT`` so the
    result never looks review-admitted. ``kb`` is accepted for signature
    parity with the review producer and is not consulted.
    """
    del kb  # the direct channel performs no graph queries
    validated = validated_case(case)
    return CalculationAuthorization(
        case=validated,
        decision="COMPUTE",
        claim_hash=claim_hash(validated.raw),
        issuer=ISSUER_ENGINE_DIRECT,
        provenance={"branch": validated.branch},
    )


def utc_now() -> str:
    """UTC issue timestamp for an authorization."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
