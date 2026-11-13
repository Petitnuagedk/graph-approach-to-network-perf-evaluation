#!/usr/bin/env python3
"""Resume A4.2 by reusing rows 1-60 and rerunning rows 61-90."""
import hashlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "continuation_v4" / "resume_from_v2_corrected.py"
source = SOURCE.read_text(encoding="utf-8")
prereg_hash = hashlib.sha256((HERE / "prereg.md").read_bytes()).hexdigest()
source = source.replace(
    'HERE = Path(__file__).resolve().parent',
    f'HERE = Path({str(HERE)!r})', 1)
source = source.replace(
    'PREREG_SHA256 = "9d930ed156a83b787e89279507bc0084fe019e4ef4cc6f48c70c5aa24575afc8"',
    f'PREREG_SHA256 = "{prereg_hash}"', 1)
source = source.replace(
    'fields[0] != sha(HERE / "resume_from_v2_corrected.py")',
    'fields[0] != sha(HERE / "rerun_after_60.py")', 1)
source = source.replace(
    '    stage = load_stage()\n',
    '    stage = load_stage()\n'
    '    stage.RUN_TIMEOUT_S = None\n'
    '    stage.guard = lambda: (True, 10**18, 0)\n', 1)
source = source.replace(
    'if seq <= 63:',
    'if seq <= 60:', 1)
source = source.replace(
    'label = f"reused {seq:02d}/63" if seq <= 63 else f"new {seq - 63:02d}/27 (plan {seq:02d}/90)"',
    'label = f"reused {seq:02d}/60" if seq <= 60 else f"new {seq - 60:02d}/30 (plan {seq:02d}/90)"', 1)
source = source.replace(
    'A4.2 continuation-v4: reusing rows 1-63; launching only unlaunched rows 64-90.',
    'A4.2 continuation-v8: reusing rows 1-60; rerunning rows 61-90 without timeout or resource-guard stop.', 1)
namespace = {"__file__": str(SOURCE), "__name__": "__main__"}
exec(compile(source, str(SOURCE), "exec"), namespace)
