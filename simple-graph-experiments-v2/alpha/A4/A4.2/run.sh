#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
EXPECTED_PREREG_SHA256=5ab4e85f5b335afabe89147e30e445bf409429c3bb8353876607719bfa5bae06
ACTUAL_PREREG_SHA256="$(sha256sum "$HERE/prereg.md" | awk '{print $1}')"
if [[ "$ACTUAL_PREREG_SHA256" != "$EXPECTED_PREREG_SHA256" ]]; then
  printf 'A4.2 preregistration hash mismatch; refusing any run.\n' >&2
  exit 2
fi
cd "$HERE/../../.."
exec /home/hledirach/Documents/J2/.venv/bin/python "$HERE/run_stage.py"
