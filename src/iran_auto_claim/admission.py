"""Calculation admission boundary.

Normal claim processing may only run on a claim authorized by ``Review.authorize``:

    review answers -> review decision -> CalculationAuthorization -> compute()

``REFUSE`` and ``INSUFFICIENT_INFORMATION`` are terminal review decisions and
cannot produce an authorization.  The authorization owns immutable canonical
snapshots of the validated claim and its provenance.  Calculation materializes
a fresh claim from that snapshot rather than trusting a live ``Case`` object.

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
from decimal import Decimal
import math
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


def _canonical_json(value: Any) -> str:
    """Encode JSON data deterministically without losing ``Decimal`` numbers."""
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=True, separators=(",", ":"))
    if isinstance(value, int):
        return str(value)
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("canonical authorization JSON requires finite numbers")
        return format(value, "f")
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("canonical authorization JSON requires finite numbers")
        return json.dumps(value, ensure_ascii=True, allow_nan=False, separators=(",", ":"))
    if isinstance(value, (list, tuple)):
        return "[" + ",".join(_canonical_json(item) for item in value) + "]"
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise TypeError("canonical authorization JSON requires string object keys")
        return "{" + ",".join(
            f"{_canonical_json(key)}:{_canonical_json(value[key])}"
            for key in sorted(value)
        ) + "}"
    raise TypeError(f"value of type {type(value).__name__} is not JSON-compatible")


def _snapshot_hash(snapshot: str) -> str:
    return "sha256:" + hashlib.sha256(snapshot.encode("utf-8")).hexdigest()


def claim_hash(payload: dict[str, Any]) -> str:
    """Content hash of a claim payload's deterministic canonical JSON."""
    return _snapshot_hash(_canonical_json(payload))


@dataclass(frozen=True)
class _AuthorizationGrant:
    """Factory-issued immutable state bound to one authorization meaning."""

    issuance_seal: object = field(repr=False, compare=False)
    claim_snapshot: str
    claim_hash: str
    provenance_snapshot: str
    decision: str
    issuer: str
    issued_at: str | None


@dataclass(frozen=True)
class CalculationAuthorization:
    """Capability proving that one issuer admitted one immutable claim snapshot.

    Attributes:
        decision: the issuing decision (``COMPUTE`` or ``SCENARIO_SET``).
        issuer: which producer issued this authorization.
        issued_at: UTC timestamp for review-issued authorizations.

    Claim and provenance snapshots are deliberately ``init=False`` inside the
    private grant. ``dataclasses.replace()`` therefore constructs an unissued
    object rather than copying issuance authority onto changed public fields.
    """

    decision: str
    issuer: str
    issued_at: str | None = None
    _grant: _AuthorizationGrant | None = field(default=None, init=False, repr=False, compare=False)

    @property
    def claim_hash(self) -> str:
        """Hash of the immutable claim snapshot, or empty for an unissued object."""
        return self._grant.claim_hash if self._grant is not None else ""

    @property
    def case(self) -> Case:
        """A fresh validated view of the authorized claim for compatibility."""
        from .schema_input import validated_case

        self.verify()
        return validated_case(self.claim_payload())

    @property
    def provenance(self) -> dict[str, Any]:
        """A detached copy of issuer-specific provenance."""
        if self._grant is None:
            return {}
        value = json.loads(self._grant.provenance_snapshot)
        return value if isinstance(value, dict) else {}

    def claim_payload(self) -> dict[str, Any]:
        """Return a fresh payload decoded from the immutable canonical snapshot."""
        if self._grant is None:
            raise AuthorizationError("authorization has no factory-issued claim snapshot")
        value = json.loads(self._grant.claim_snapshot)
        if not isinstance(value, dict):  # defensive; factories only admit objects
            raise AuthorizationError("authorized claim snapshot is not an object")
        return value

    def verify(self) -> None:
        """Fail closed unless factory identity and every bound field still match."""
        grant = self._grant
        if grant is None:
            raise AuthorizationError(
                "authorization was not issued by an approved factory; run normal "
                "claims through Review.authorize() before calculation"
            )
        if not (
            (
                grant.issuance_seal is _REVIEW_ISSUANCE_SEAL
                and self.issuer == ISSUER_REVIEW
            )
            or (
                grant.issuance_seal is _INTERNAL_TEST_ISSUANCE_SEAL
                and self.issuer == ISSUER_INTERNAL_TEST
            )
        ) or not (
            grant.decision == self.decision
            and grant.issuer == self.issuer
            and grant.issued_at == self.issued_at
        ):
            raise AuthorizationError(
                "authorization metadata does not match its factory-issued capability"
            )
        if self.decision not in AUTHORIZED_DECISIONS:
            raise AuthorizationError(
                f"decision {self.decision!r} does not authorize calculation; "
                f"only {', '.join(sorted(AUTHORIZED_DECISIONS))} may"
            )
        if _snapshot_hash(grant.claim_snapshot) != grant.claim_hash:
            raise AuthorizationError(
                "claim snapshot no longer matches its factory-issued authorization hash"
            )

    def provenance_record(self) -> dict[str, Any]:
        """Return a detached copy of the immutable issuance provenance."""
        self.verify()
        record = self.provenance
        record.update(
            {
                "issuer": self.issuer,
                "decision": self.decision,
                "claim_hash": self.claim_hash,
                "issued_at": self.issued_at,
            }
        )
        return record


def utc_now() -> str:
    """UTC issue timestamp for an authorization."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _issue_authorization(
    payload: dict[str, Any] | Case,
    *,
    decision: str,
    issuer: str,
    issued_at: str | None,
    provenance: dict[str, Any],
    issuance_seal: object,
) -> CalculationAuthorization:
    """Validate and immutably bind one factory-issued authorization."""
    from .schema_input import validated_case

    case = validated_case(payload)
    claim_snapshot = _canonical_json(case.raw)
    # Prove the exact representation compute() will later materialize remains a
    # valid claim at the issuance boundary.
    validated_case(json.loads(claim_snapshot))
    provenance_snapshot = _canonical_json(provenance)
    decoded_provenance = json.loads(provenance_snapshot)
    if not isinstance(decoded_provenance, dict):
        raise TypeError("authorization provenance must be a JSON object")

    authorization = CalculationAuthorization(
        decision=decision,
        issuer=issuer,
        issued_at=issued_at,
    )
    object.__setattr__(
        authorization,
        "_grant",
        _AuthorizationGrant(
            issuance_seal=issuance_seal,
            claim_snapshot=claim_snapshot,
            claim_hash=_snapshot_hash(claim_snapshot),
            provenance_snapshot=provenance_snapshot,
            decision=decision,
            issuer=issuer,
            issued_at=issued_at,
        ),
    )
    return authorization


def _issue_review_authorization(
    payload: dict[str, Any] | Case,
    *,
    decision: str,
    issued_at: str,
    provenance: dict[str, Any],
) -> CalculationAuthorization:
    """Private factory used only by ``Review.authorize()`` for normal claims."""
    return _issue_authorization(
        payload,
        decision=decision,
        issuer=ISSUER_REVIEW,
        issued_at=issued_at,
        provenance=provenance,
        issuance_seal=_REVIEW_ISSUANCE_SEAL,
    )


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

    return _issue_authorization(
        payload,
        decision=decision,
        issuer=ISSUER_INTERNAL_TEST,
        issued_at=utc_now(),
        provenance={
            "authorization_kind": "INTERNAL_TEST_DIRECT",
            "purpose": purpose,
        },
        issuance_seal=_INTERNAL_TEST_ISSUANCE_SEAL,
    )
