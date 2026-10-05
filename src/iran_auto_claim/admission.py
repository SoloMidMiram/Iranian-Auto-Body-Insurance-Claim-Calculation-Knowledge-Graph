"""Calculation admission boundary.

Normal claim processing may only run on a claim authorized by ``Review.authorize``:

    review answers -> review decision -> CalculationAuthorization -> compute()

``REFUSE`` and ``INSUFFICIENT_INFORMATION`` are terminal review decisions and
cannot produce an authorization.  The authorization also binds the exact
validated payload by content hash, so editing a case after review invalidates
the authorization before arithmetic starts.

Python cannot provide an unforgeable in-process capability to code that can
mutate or introspect the interpreter.  Private issuance seals nevertheless make
the supported boundary explicit and fail-closed: constructing the public domain
object directly does not create an authorization accepted by the engine.

Normal claims use the review seal exclusively.  A separately marked internal
seal exists only for fixtures, mutation probes, and isolated arithmetic tests;
it cannot masquerade as ``REVIEW_GATE`` and is not exported by the package API.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .case import Case

ISSUER_REVIEW = "REVIEW_GATE"
ISSUER_INTERNAL_TEST = "INTERNAL_TEST_DIRECT"

# Private capability used by Review.authorize().  It is intentionally not
# exported from the package and is verified again at the engine boundary.
_REVIEW_ISSUANCE_SEAL = object()
_INTERNAL_TEST_ISSUANCE_SEAL = object()

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
    _issuance_seal: object | None = field(default=None, repr=False, compare=False)

    def verify(self) -> None:
        """Fail closed unless the decision authorizes and the payload matches."""
        if not (
            (self._issuance_seal is _REVIEW_ISSUANCE_SEAL and self.issuer == ISSUER_REVIEW)
            or (
                self._issuance_seal is _INTERNAL_TEST_ISSUANCE_SEAL
                and self.issuer == ISSUER_INTERNAL_TEST
            )
        ):
            raise AuthorizationError(
                "authorization was not issued by an approved factory; run normal "
                "claims through Review.authorize() before calculation"
            )
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


def utc_now() -> str:
    """UTC issue timestamp for an authorization."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _internal_test_direct_authorize(
    payload: dict[str, Any] | Case,
    *,
    decision: str = "COMPUTE",
    purpose: str,
) -> CalculationAuthorization:
    """Authorize an isolated calculation outside normal claim processing.

    This private helper exists for authored fixtures, mutation probes, and
    arithmetic unit tests only.  It still applies the public claim schema and
    produces provenance that is visibly distinct from a review authorization.
    Production commands never call it and there is no automatic fallback to it.
    """
    if decision not in AUTHORIZED_DECISIONS:
        raise AuthorizationNotGranted(
            f"internal test decision {decision!r} does not authorize calculation"
        )

    # Imported lazily to keep the admission domain independent of schema loading
    # during module initialization.
    from .schema_input import validated_case

    case = validated_case(payload)
    return CalculationAuthorization(
        case=case,
        decision=decision,
        claim_hash=claim_hash(case.raw),
        issuer=ISSUER_INTERNAL_TEST,
        issued_at=utc_now(),
        provenance={
            "authorization_kind": "INTERNAL_TEST_DIRECT",
            "purpose": purpose,
        },
        _issuance_seal=_INTERNAL_TEST_ISSUANCE_SEAL,
    )
