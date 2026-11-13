#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
EXPECTED_PREREG_SHA256=5d203dc1f1201f2d5f06512d1653d6eb2ba3a77cb6226f6af35eaf378ce3058e
EXPECTED_FROZEN_RUNNER_SHA256=a189cb06c224dbaff84c79626ae5736f703f5e843ade7e35aad47827bbbe11ec
EXPECTED_PILOT_RUNNER_SHA256=f7f89864df756a157327f61e73c1e11f635aaf7ddf16fea024419e35012e3c45
EXPECTED_SWEEP_RUNNER_SHA256=ace985c7c48696c5545b98eb0c72c650c9a16ebd76f6f3f11a368275d7761666
ACTUAL_PREREG_SHA256="$(sha256sum "$HERE/prereg.md" | awk '{print $1}')"
ACTUAL_FROZEN_RUNNER_SHA256="$(sha256sum "$HERE/../run_stage.py" | awk '{print $1}')"
ACTUAL_PILOT_RUNNER_SHA256="$(sha256sum "$HERE/run_pilots.py" | awk '{print $1}')"
ACTUAL_SWEEP_RUNNER_SHA256="$(sha256sum "$HERE/run_sweep.py" | awk '{print $1}')"
if [[ "$ACTUAL_PREREG_SHA256" != "$EXPECTED_PREREG_SHA256" ]]; then
  printf 'A4.2 repair-v1 preregistration hash mismatch; refusing any run.\n' >&2
  exit 2
fi
if [[ "$ACTUAL_FROZEN_RUNNER_SHA256" != "$EXPECTED_FROZEN_RUNNER_SHA256" ]]; then
  printf 'Frozen A4.2 runner hash mismatch; refusing any run.\n' >&2
  exit 2
fi
if [[ "$ACTUAL_PILOT_RUNNER_SHA256" != "$EXPECTED_PILOT_RUNNER_SHA256" || "$ACTUAL_SWEEP_RUNNER_SHA256" != "$EXPECTED_SWEEP_RUNNER_SHA256" ]]; then
  printf 'A4.2 repair execution script hash mismatch; refusing any run.\n' >&2
  exit 2
fi
cd "$HERE"
/home/hledirach/Documents/J2/.venv/bin/python "$HERE/run_pilots.py"
/home/hledirach/Documents/J2/.venv/bin/python "$HERE/run_sweep.py"
