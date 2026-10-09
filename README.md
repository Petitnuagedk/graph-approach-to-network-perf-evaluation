# J2

This project generates icosahedral geodesic graphs, exports them to CSV adjacency matrices, and builds dynamic graphs for a selected source-destination pair before running the network simulation pipeline.

## Overview

The workspace contains scripts for:

- generating geodesic polyhedron graphs from icosahedral subdivisions,
- saving graph data for downstream processing,
- building dynamic graphs using the SPC pipeline,
- running a larger G -> DG -> ns-3 replay workflow,
- exploring parameter sweeps and plot generation.

## Main files

- `icosahedral_geodesic.py` — core geodesic graph generation logic.
- `geodesic-generator-exemple.py` — example usage and visualization helpers.
- `G2DG-SPC.py` — loads a graph and builds a dynamic graph for a chosen pair.
- `run_pipeline.py` — end-to-end pipeline supervisor for graph generation, dynamic graph creation, ns-3 execution, and optional plotting.
- `sweep.py` and `run_pipeline-sweep.py` — parameter sweep utilities.
- `run_simple_graph_experiments.py` — starter matrix for line, two-lines, and ladder graphs.
- `plot.py` — plotting helpers for generated metrics/results.

## Project folders

- `Graph/` — generated graph files and dynamic-frame outputs.
- `pipeline-out/` — pipeline output directory used by the supervisor script.
- `p-m2/` and `p-m3/` — experiment/result folders for different settings.
- `SG/` — additional graph data.

## Quick start

### 1) Generate the graph and dynamic graph

```bash
python3 run_pipeline.py --work-dir pipeline-out --stages graph,dg
```

This runs the graph generation stage and then creates a dynamic graph for a selected pair.

### 2) Run the full pipeline

```bash
python3 run_pipeline.py --work-dir pipeline-out --stages graph,dg,sim,plot
```

This is the full workflow described in the script: static graph -> dynamic graph -> ns-3 replay -> plots.

## Notes

- The dynamic graph code expects a compatible `yadygaga` Python package on the import path.
- Run `python3 run_simple_graph_experiments.py` to generate the three small-graph SPC sweeps and their measured DG-property CSVs. Add `--ns3-dir <ns-3-root>` for a full run, or use `--ns3-dir <ns-3-root> --stages sim,plot` to reuse existing DGs. Use `--properties-only` to plot DG diagnostics without ns-3.
- Each DG now has a `properties.csv` with achieved S–R uptime, up/down run lengths, and shortest-route identity retention. Full pipeline plots include these realized properties alongside ns-3 outcomes.
- Output files are stored under `Graph/` and `pipeline-out/` unless a different work directory is passed.
- The scripts use NetworkX and NumPy heavily for graph construction and analysis.

## Dynamic simple-graph campaign v2 (Phase 2 instrumentation)

The v2 runner writes to `simple-graph-experiments-v2/` by default; the existing
`simple-graph-experiments/` campaign is treated as read-only. The v2 runner
passes a 45 s same-topology warm-up (`--warmup-mode first`) by default. Direct
calls to `run_pipeline-sweep.py` retain the legacy 0 s warm-up default unless
`--warmup` is supplied. The v2 runner and pipeline use a 125 dB link-down loss.
The down loss is below the TMLM sparse threshold (150 dB), so it remains an
explicit stored value during interpolation while remaining below the PHY's
receive sensitivity. Every work root, generated DG, and ns-3 replay epoch gets
a `config.json` with arguments, derived seeds, timestamps, source hashes, git
revision (when available), and ns-3 commit/version (when available).

Replay CSVs count offered packets at `UdpClient::Tx` (before routing can drop
them), include oracle S–R uptime/run/outage/route-retention data from the trace,
routing efficiency, per-outage re-establishment delays, and the oracle-path
static-route baseline. Control overhead is counted from non-application IPv4
Tx packets; control bytes use the IPv4 packet size. OLSR message types are read
from OLSR headers; AODV types from its type/RREP headers (RREP with equal
destination and origin is HELLO); DSDV packets are DSDV updates. These are
transmitted protocol packet counts/bytes, not a FlowMonitor estimate.

`plot.py` averages replay epochs within each graph realization first, then
plots realization means with deterministic percentile-bootstrap 95% confidence
intervals. The aggregate CSV records `n_realizations` and `n_epochs`.

Small reproducible Phase 2 smoke campaign (one DG realization, one replay
epoch; four ns-3 runs: OLSR, AODV, DSDV, static):

```bash
python3 run_pipeline-sweep.py \
	--work-dir simple-graph-experiments-v2/phase2/ladder-smoke \
	--stages graph,dg,sim,plot \
	--topology ladder --topology-length 3 --pair-a S --pair-b R \
	--dg-frames 60 --path-life 0.9 --stability 0.8 \
	--path-persistency 0.75 --epoch 1 --seed 42 \
	--warmup 45 --warmup-mode first --link-down-loss-db 125 \
	--include-static-baseline --ns3-dir /path/to/ns-3
```

Run the hand-built oracle-metric reference checks with
`python3 tests/test_oracle_metrics.py`. These validate expected uptime, run
lengths, transitions, alternative-path retention, and outage durations.

## Typical dependencies

- Python 3
- NetworkX
- NumPy
- Matplotlib
- `yadygaga` (for dynamic graph generation)

## License

This project does not currently include a license file. Check with the repository owner before redistributing or publishing it.
