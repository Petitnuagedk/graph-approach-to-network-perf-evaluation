#!/usr/bin/env bash
set -eu
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "B0 preparation only: no Beta run launched"
echo "Feasibility table: $ROOT/feasibility_F300.csv"
echo "Pinned source provenance: $ROOT/source_provenance.json"
