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
- Output files are stored under `Graph/` and `pipeline-out/` unless a different work directory is passed.
- The scripts use NetworkX and NumPy heavily for graph construction and analysis.

## Typical dependencies

- Python 3
- NetworkX
- NumPy
- Matplotlib
- `yadygaga` (for dynamic graph generation)

## License

This project does not currently include a license file. Check with the repository owner before redistributing or publishing it.
