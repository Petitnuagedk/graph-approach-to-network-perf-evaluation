#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
EXPECTED_PREREG_SHA256=66d4f765650d668ce01df786bd89996f018f70f05f8e5119bb7e9a73d538f548
ACTUAL_PREREG_SHA256="$(sha256sum "$HERE/prereg.md" | awk '{print $1}')"
if [[ "$ACTUAL_PREREG_SHA256" != "$EXPECTED_PREREG_SHA256" ]]; then
  printf 'A4.1c preregistration hash mismatch; refusing analysis.\n' >&2
  exit 2
fi
cd "$HERE/../../.."
exec /home/hledirach/Documents/J2/.venv/bin/python "$HERE/analyze.py"
