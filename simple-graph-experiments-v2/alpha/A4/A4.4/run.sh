#!/usr/bin/env bash
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="/home/hledirach/Documents/J2/.venv/bin/python"
EXPECTED="eeeb1850b4cbf4a53358a2e274df17c5973b08876f8d3ae1c4490cd6eeb938d7"
if [[ "$(sha256sum "$ROOT/prereg.md" | awk '{print $1}')" != "$EXPECTED" ]]; then echo 'preregistration hash mismatch; refusing' >&2; exit 2; fi
AMENDMENT="14798b396e37dbf93e609ccae9c68d690495cc83f65dc2518a3158836c48e2ea"
[[ "$(sha256sum "$ROOT/amendment_1.md" | awk '{print $1}')" == "$AMENDMENT" ]] || { echo 'amendment hash mismatch; refusing'; exit 2; }
case "${1:-smoke}" in
	smoke) exec "$PYTHON" "$ROOT/run.py" smoke ;;
	run) "$PYTHON" "$ROOT/run.py" smoke && exec "$PYTHON" "$ROOT/run.py" run ;;
	*) exec "$PYTHON" "$ROOT/run.py" "$1" ;;
esac
