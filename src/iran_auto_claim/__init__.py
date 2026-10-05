"""Iranian motor claim calculation knowledge graph and rule engine."""

from .admission import (
    AUTHORIZED_DECISIONS,
    AuthorizationError,
    AuthorizationNotGranted,
    CalculationAuthorization,
    claim_hash,
)
from .engine import compute, CalcResult
from .knowledge import Knowledge, Node
from .case import Case, CaseInputError

__all__ = [
    "compute",
    "CalcResult",
    "Knowledge",
    "Node",
    "Case",
    "CaseInputError",
    "CalculationAuthorization",
    "AuthorizationError",
    "AuthorizationNotGranted",
    "AUTHORIZED_DECISIONS",
    "claim_hash",
]
__version__ = "1.0.0"
