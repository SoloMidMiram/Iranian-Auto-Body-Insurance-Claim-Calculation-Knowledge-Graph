import os
import sys

_ROOT = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.join(_ROOT, "src")

for _p in (_SRC, _ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)
