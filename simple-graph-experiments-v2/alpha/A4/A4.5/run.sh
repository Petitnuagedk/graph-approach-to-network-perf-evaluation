#!/usr/bin/env bash
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="/home/hledirach/Documents/J2/.venv/bin/python"
EXPECTED="8cc36361941e22b462397dc2782d4aba76584d7a7d048d014a1f0a606e90a466"
if [[ "$(sha256sum "$ROOT/prereg.md" | awk '{print $1}')" != "$EXPECTED" ]]; then echo 'preregistration hash mismatch; refusing' >&2; exit 2; fi
AMENDMENT="14798b396e37dbf93e609ccae9c68d690495cc83f65dc2518a3158836c48e2ea"
[[ "$(sha256sum "$ROOT/amendment_1.md" | awk '{print $1}')" == "$AMENDMENT" ]] || { echo 'amendment hash mismatch; refusing'; exit 2; }
case "${1:-smoke}" in
	smoke) exec "$PYTHON" "$ROOT/run.py" smoke ;;
	run) "$PYTHON" "$ROOT/run.py" smoke && exec "$PYTHON" "$ROOT/run.py" run ;;
	*) exec "$PYTHON" "$ROOT/run.py" "$1" ;;
esac
