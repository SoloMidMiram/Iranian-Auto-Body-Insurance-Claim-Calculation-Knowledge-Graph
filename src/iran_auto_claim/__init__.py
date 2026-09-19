"""Iranian motor claim calculation knowledge graph and rule engine."""

from .engine import compute, CalcResult
from .knowledge import Knowledge, Node
from .case import Case, CaseInputError

__all__ = ["compute", "CalcResult", "Knowledge", "Node", "Case", "CaseInputError"]
__version__ = "1.0.0"
