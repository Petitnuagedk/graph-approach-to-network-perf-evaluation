#!/usr/bin/env bash
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="/home/hledirach/Documents/J2/.venv/bin/python"
EXPECTED="6d35e9490b48799f40704b7dd2b1ca674c6bd95d467fbf547ba4dbe4532f413f"
[[ "$(sha256sum "$ROOT/prereg_amendment_2.md" | awk '{print $1}')" == "$EXPECTED" ]] || { echo 'amendment 2 hash mismatch; refusing'; exit 2; }
exec "$PYTHON" - "$ROOT" "${1:-plan}" <<'PY'
import sys
from pathlib import Path
root=Path(sys.argv[1])
source=(root/'run_amendment_1.sh').read_text()
body=source.split("<<'PY'\n",1)[1].rsplit('\nPY',1)[0]
replacements={
 'PHI=((1,.01),(2,.02),(3,.03),(4,.04),(5,.05))':'PHI=((6,.06),(7,.07),(8,.08),(9,.09),(10,.10))',
 "ROOT/'plan_amendment_1.csv'":"ROOT/'plan_amendment_2.csv'",
 "ROOT/'per_run_amendment_1.csv'":"ROOT/'per_run_amendment_2.csv'",
 "ROOT/'control_by_type_amendment_1.csv'":"ROOT/'control_by_type_amendment_2.csv'",
}
for old,new in replacements.items():
 if old not in body: raise SystemExit(f'missing expected runner text: {old}')
 body=body.replace(old,new)
exec(compile(body,'run_amendment_2_embedded.py','exec'),{'__name__':'__main__'})
PY
