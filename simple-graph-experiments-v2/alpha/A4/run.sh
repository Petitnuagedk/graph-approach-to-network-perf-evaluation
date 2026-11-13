#!/usr/bin/env bash
set -euo pipefail

J2=/home/hledirach/Documents/J2
STUDY="$J2/simple-graph-experiments-v2"
A4="$STUDY/alpha/A4"
NS3_TREE=/home/hledirach/Documents/sp1-sp2
PYTHON=/home/hledirach/Documents/J2/.venv/bin/python

if [[ $# -ne 1 ]]; then
    echo "Usage: $0 {4.0|4.1|4.2|4.3}" >&2
    exit 2
fi
case "$1" in
    4.0)
        cd "$NS3_TREE"
        ./ns3 build scratch/graph-run 2>&1 | tee "$A4/build.log"
        exec "$PYTHON" "$A4/a4.py" 4.0
        ;;
    4.1|4.2|4.3)
        cd "$NS3_TREE"
        exec "$PYTHON" "$A4/a4.py" "$1"
        ;;
    *)
        echo "Unknown A4 stage: $1" >&2
        exit 2
        ;;
esac
