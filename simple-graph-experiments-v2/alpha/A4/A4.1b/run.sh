#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
EXPECTED_PREREG_SHA256=6d26c7359008e64ab1975a644f7e59d6fa320143396c5f53b0f3c7998c992a35
ACTUAL_PREREG_SHA256="$(sha256sum "$HERE/prereg.md" | awk '{print $1}')"
if [[ "$ACTUAL_PREREG_SHA256" != "$EXPECTED_PREREG_SHA256" ]]; then
  printf 'A4.1b preregistration hash mismatch; refusing analysis.\n' >&2
  exit 2
fi
cd "$HERE/../../.."
exec /home/hledirach/Documents/J2/.venv/bin/python "$HERE/analyze.py"
