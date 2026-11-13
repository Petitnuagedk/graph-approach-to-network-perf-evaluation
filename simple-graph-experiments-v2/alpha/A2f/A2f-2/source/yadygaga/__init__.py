"""A2f isolated overlay; untouched modules resolve from the A2d item 1 parent."""
import os
from pathlib import Path

_BASELINE_SOURCE = os.environ.get("A2F_BASELINE_SOURCE")
if _BASELINE_SOURCE:
    _A2D1_MODULES = Path(_BASELINE_SOURCE).resolve() / "yadygaga"
else:
    _A2F_ALPHA = Path(__file__).resolve().parents[4]
    _A2D1_MODULES = _A2F_ALPHA / "A2" / "A2d" / "item1" / "source" / "yadygaga"
if str(_A2D1_MODULES) not in __path__:
    __path__.append(str(_A2D1_MODULES))
