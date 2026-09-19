"""Convenience launcher so the CLI runs from a source checkout without installing.

    python claim.py calc cases/example_partial.json
    python claim.py fixtures
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from iran_auto_claim.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
