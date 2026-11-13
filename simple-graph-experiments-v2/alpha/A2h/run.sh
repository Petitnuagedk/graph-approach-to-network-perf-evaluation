#!/usr/bin/env bash
set -euo pipefail
ROOT="/home/hledirach/Documents/J2/simple-graph-experiments-v2"
PYTHON="/home/hledirach/Documents/J2/.venv/bin/python"
cd "$ROOT"
"$PYTHON" alpha/A2h/run_a2h.py --distortion
"$PYTHON" alpha/A2h/run_a2h.py --chain-grid
"$PYTHON" alpha/A2h/run_a2h.py --missing-pool
"$PYTHON" alpha/A2h/run_a2h.py --manifest
