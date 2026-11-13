#!/usr/bin/env bash
set -euo pipefail

J2=/home/hledirach/Documents/J2
STUDY="$J2/simple-graph-experiments-v2"
NS3_TREE=/home/hledirach/Documents/sp1-sp2
A3B="$STUDY/alpha/A3b"
T1_FIXTURE="$STUDY/alpha/A3/fixtures/t1_four_node_path.csv"
B0_TRACE="$STUDY/phase5/line/path_life/dynamic_frames/graph_0001/path_life_0.7000/frames.csv"
GEO="$J2/SG/geodesic_adjacency_matrix.csv"
PYTHON=/home/hledirach/Documents/J2/.venv/bin/python

# Fail closed on a second invocation: the registration permits each variant once.
for path in "$A3B/T2T3" "$A3B/T1" "$A3B/T4"; do
    if [[ -e "$path" ]]; then
        echo "Refusing to rerun: output already exists: $path" >&2
        exit 2
    fi
done
cd "$NS3_TREE"
./ns3 build scratch/graph-run 2>&1 | tee "$A3B/build.log"
mkdir -p "$A3B/T2T3" "$A3B/T1" "$A3B/T4"

timeout 60s ./ns3 run "scratch/graph-run --framesCsv=$GEO --outDir=$A3B/T2T3 --routing=olsr --a3SelfTest=true --seed=42 --fps=1 --linkUpLossDb=10 --linkDownLossDb=125" \
    2>&1 | tee "$A3B/T2T3/ns3_selftest.log"
"$PYTHON" "$A3B/validate_offline.py" 2>&1 | tee "$A3B/T2T3/networkx_validation.log"

timeout 60s ./ns3 run "scratch/graph-run --framesCsv=$T1_FIXTURE --outDir=$A3B/T1 --routing=olsr,aodv --flows=Node_0:Node_3 --dataRate=50kbps --packetSize=1024 --lossThresholdDb=150 --interpolate=true --defaultLossDb=1000000 --txPowerDbm=20 --linkUpLossDb=10 --linkDownLossDb=200 --fps=1 --seed=42 --warmup=30 --warmupMode=first --dumpRoutes=true --instrumentation=true --flowFraction=0 --flowSeed=9001 --a3bForwardLog=true" \
    2>&1 | tee "$A3B/T1/ns3_run.log"

timeout 60s ./ns3 run "scratch/graph-run --framesCsv=$B0_TRACE --outDir=$A3B/T4 --routing=olsr,aodv --flows=S:R --dataRate=50kbps --packetSize=1024 --lossThresholdDb=150 --interpolate=true --defaultLossDb=1000000 --txPowerDbm=20 --linkUpLossDb=10 --linkDownLossDb=125 --fps=1 --seed=42 --warmup=45 --warmupMode=first --dumpRoutes=true" \
    2>&1 | tee "$A3B/T4/ns3_run.log"
