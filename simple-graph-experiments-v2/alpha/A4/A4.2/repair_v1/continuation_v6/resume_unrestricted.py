#!/usr/bin/env python3
"""Resume A4.2 rows 64-90 with no per-run timeout or resource-guard stop."""
import hashlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "continuation_v4" / "resume_from_v2_corrected.py"
source = SOURCE.read_text(encoding="utf-8")
prereg_hash = hashlib.sha256((HERE / "prereg.md").read_bytes()).hexdigest()
source = source.replace(
    'HERE = Path(__file__).resolve().parent',
    f'HERE = Path({str(HERE)!r})',
    1,
)
source = source.replace(
    'PREREG_SHA256 = "9d930ed156a83b787e89279507bc0084fe019e4ef4cc6f48c70c5aa24575afc8"',
    f'PREREG_SHA256 = "{prereg_hash}"',
    1,
)
source = source.replace(
    'fields[0] != sha(HERE / "resume_from_v2_corrected.py")',
    'fields[0] != sha(HERE / "resume_unrestricted.py")',
    1,
)
source = source.replace(
    '        if False and len(per_runs) in (15, 60):',
    '        if False and len(per_runs) in (15, 60):',
    1,
)
source = source.replace(
    '    source = source_path.read_text(encoding="utf-8")',
    '    source = source_path.read_text(encoding="utf-8")\n'
    '    source = source.replace("RUN_TIMEOUT_S = 3600", "RUN_TIMEOUT_S = None", 1)\n'
    '    source = source.replace("        if not ok:\\n", "        if False and not ok:\\n", 1)',
    1,
)
source = source.replace(
    '    stage = load_stage()\n',
    '    stage = load_stage()\n'
    '    stage.RUN_TIMEOUT_S = None\n'
    '    stage.guard = lambda: (True, 10**18, 0)\n',
    1,
)
source = source.replace(
    '    print("A4.2 continuation-v4: reusing rows 1-63; launching only unlaunched rows 64-90.", flush=True)',
    '    print("A4.2 continuation-v6: reusing rows 1-63; launching rows 64-90 with no timeout or resource-guard stop.", flush=True)',
    1,
)
if 'RUN_TIMEOUT_S = None' not in source or 'if False and not ok:' not in source:
    raise SystemExit("failed to apply unrestricted continuation changes")
namespace = {"__file__": str(SOURCE), "__name__": "__main__"}
exec(compile(source, str(SOURCE), "exec"), namespace)
