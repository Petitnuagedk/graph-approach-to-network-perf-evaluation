#!/usr/bin/env python3
"""Fresh-output retry of the corrected A4.2 continuation runner."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "continuation_v4" / "resume_from_v2_corrected.py"
source = SOURCE.read_text(encoding="utf-8")
source = source.replace(
    'HERE = Path(__file__).resolve().parent',
    f'HERE = Path({str(HERE)!r})',
    1,
)
namespace = {"__file__": str(SOURCE), "__name__": "__main__"}
exec(compile(source, str(SOURCE), "exec"), namespace)
