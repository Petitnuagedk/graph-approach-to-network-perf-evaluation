# Phase 5 report: topology and DG-property sweeps

## Scope and design

Phase 5 tests how three graph families respond to one-at-a-time sweeps of path life, stability, and path persistency. The full campaign ran in the isolated v2 output tree; the original `simple-graph-experiments/` campaign and Phase 1–4 outputs were not modified. This report closes Phase 5 only. Phase 6 has not been started.

| Setting | Value |
|---|---|
| Topologies | `line`, `two-lines`, `ladder`; topology length 3 |
| Flow pair | S→R |
| DG frames / temporal scale | 60 / 1.0 frame/s |
| Swept path life | 0.1, 0.3, 0.5, 0.7, 0.9 |
| Swept stability | 0.0, 0.2, 0.4, 0.6, 0.8 |
| Swept path persistency | 0, 0.25, 0.5, 0.75, 1.0 |
| Fixed DG settings | Non-swept parameters held at path life 0.5, stability 0.8, persistency 0.75 |
| Graph realizations / replay epochs | 5 / 5 per sweep value |
| Base seed | 42; individual DG/replay seeds are recorded in the per-case configs |
| Routing variants | OLSR, AODV, static oracle-route reference |
| Replay settings | 45 s `first`-frame warm-up; 125 dB link-down loss; 10 dB link-up loss; interpolation on; 50 kbps; 1024-byte packets; 802.11g ad-hoc; 20 dBm |
| Protocols excluded | DSDV, per instruction: its convergence anomaly remains unresolved and was not investigated or ranked |

Each parameter/topology cell contains five parameter values × five independently seeded DG realizations × five replay epochs. Replay epochs were averaged within each DG realization; the reported mean and population SD are then across the five realization means. The 95% confidence intervals are deterministic percentile-bootstrap intervals over those five realization means. Thus each plotted/table entry has `n_realizations=5` and `n_epochs=25`; epochs are not treated as independent graph realizations.

## Completion and validation

All nine pipeline invocations completed successfully. Across the campaign, validation found:

- 9 completed sweep pipelines and 1,125 replay executions.
- 225 serialized DG traces (25 per topology/parameter cell), 1,125 epoch result CSVs (125 per cell), and 3,375 protocol rows in summaries (375 per cell).
- 135 aggregate rows (15 per cell), all with five realizations and 25 replay epochs; 105 PNG plots (11 for each `line` cell and 12 for each other cell).
- Exactly the requested five parameter values per cell and exactly OLSR/AODV/static variants. No zero or non-finite PDR rows were found.
- The saved DG-property summaries contain 25 measured traces per cell. Mean serialized-trace S–R uptime equals the requested swept path-life values; for stability and path-persistency sweeps it remains 0.5, as requested by the fixed path-life setting.

NaNs are limited to two fields with defined reasons. `oracle_path_identity_retention` is undefined when there is no alternative path, or when no pair of adjacent frames is connected to compare a route identity; re-computation of this condition matched every such summary row. `reestablishment_times_s` is list-valued and can contain `nan` for an outage with no delivered packet before the next break or trace end. There are 1,740 undefined path-retention row values and 86 undefined re-establishment list entries; there are no unexplained scalar NaNs. These values are not treated as PDR or campaign failures.

The per-cell source configs record ns-3 3.46.1, base parameters, case-specific sweep values, seeds, routing arguments, warm-up, loss settings, and SHA-256 source hashes. The ns-3 directory is not a git repository, so its commit hash is unavailable. The source tree was dirty during the run; the recorded hashes are the reproducibility identifier for the relevant scripts/source files.

## PDR results

**Retrospective interpretation note (2026-10-08):** the stored/derived quotient `routing_efficiency = PDR / oracle uptime` for Phase 5 is **not interpretable as an efficiency, probability, normalized score, bound, or delivery ceiling**. Phase 7B demonstrated that packets offered while a frame is down can be buffered and delivered during a later up frame, allowing PDR/oracle-uptime ratios above 1; Phase 6 observed ratios below 1. Neither direction is a bound. Historical quotient values, if present in summary files or plots, are retained only as descriptive arithmetic; do not use them for protocol ranking, normalization, or ceiling claims. Interpret PDR and oracle uptime separately. The Phase 5 raw inputs, outputs, and numeric results are unchanged.

Each cell below reports mean PDR across the five DG-realization means with the deterministic bootstrap 95% CI in brackets. These are descriptive outcomes for this design and traffic schedule, not a general protocol ranking. The static variant is a measured oracle-route reference under the same MAC/PHY, not guaranteed delivery.

### Line topology

#### Path-life sweep

| Path life | OLSR | AODV | Static reference |
|---:|---:|---:|---:|
| 0.1 | 0.089 [0.069, 0.111] | 0.222 [0.183, 0.267] | 0.081 [0.081, 0.081] |
| 0.3 | 0.197 [0.144, 0.250] | 0.506 [0.457, 0.568] | 0.275 [0.275, 0.275] |
| 0.5 | 0.547 [0.486, 0.596] | 0.683 [0.648, 0.719] | 0.467 [0.467, 0.467] |
| 0.7 | 0.803 [0.799, 0.807] | 0.933 [0.915, 0.953] | 0.661 [0.661, 0.661] |
| 0.9 | 0.956 [0.954, 0.958] | 0.982 [0.981, 0.983] | 0.869 [0.869, 0.869] |

#### Stability sweep

| Stability | OLSR | AODV | Static reference |
|---:|---:|---:|---:|
| 0.0 | 0.768 [0.759, 0.777] | 0.909 [0.901, 0.914] | 0.368 [0.367, 0.368] |
| 0.2 | 0.715 [0.704, 0.725] | 0.819 [0.755, 0.880] | 0.392 [0.392, 0.393] |
| 0.4 | 0.689 [0.678, 0.700] | 0.845 [0.833, 0.865] | 0.417 [0.417, 0.418] |
| 0.6 | 0.610 [0.593, 0.632] | 0.814 [0.790, 0.842] | 0.444 [0.444, 0.444] |
| 0.8 | 0.547 [0.492, 0.593] | 0.683 [0.648, 0.720] | 0.467 [0.467, 0.467] |

#### Path-persistency sweep

| Path persistency | OLSR | AODV | Static reference |
|---:|---:|---:|---:|
| 0.00 | 0.548 [0.489, 0.613] | 0.711 [0.620, 0.829] | 0.467 [0.467, 0.467] |
| 0.25 | 0.499 [0.446, 0.544] | 0.651 [0.577, 0.721] | 0.467 [0.467, 0.467] |
| 0.50 | 0.571 [0.509, 0.633] | 0.676 [0.623, 0.730] | 0.467 [0.467, 0.467] |
| 0.75 | 0.547 [0.491, 0.593] | 0.683 [0.648, 0.720] | 0.467 [0.467, 0.467] |
| 1.00 | 0.556 [0.510, 0.593] | 0.596 [0.467, 0.725] | 0.467 [0.467, 0.467] |

### Two-lines topology

#### Path-life sweep

| Path life | OLSR | AODV | Static reference |
|---:|---:|---:|---:|
| 0.1 | 0.105 [0.076, 0.136] | 0.250 [0.173, 0.326] | 0.081 [0.081, 0.081] |
| 0.3 | 0.220 [0.174, 0.266] | 0.532 [0.459, 0.621] | 0.271 [0.267, 0.274] |
| 0.5 | 0.337 [0.305, 0.368] | 0.693 [0.629, 0.783] | 0.459 [0.455, 0.463] |
| 0.7 | 0.470 [0.372, 0.573] | 0.873 [0.852, 0.897] | 0.651 [0.646, 0.656] |
| 0.9 | 0.617 [0.546, 0.688] | 0.940 [0.927, 0.952] | 0.848 [0.843, 0.853] |

#### Stability sweep

| Stability | OLSR | AODV | Static reference |
|---:|---:|---:|---:|
| 0.0 | 0.419 [0.382, 0.443] | 0.807 [0.795, 0.818] | 0.368 [0.367, 0.369] |
| 0.2 | 0.398 [0.365, 0.430] | 0.762 [0.726, 0.800] | 0.392 [0.391, 0.392] |
| 0.4 | 0.348 [0.324, 0.368] | 0.732 [0.660, 0.788] | 0.416 [0.414, 0.417] |
| 0.6 | 0.341 [0.283, 0.386] | 0.780 [0.712, 0.850] | 0.439 [0.436, 0.442] |
| 0.8 | 0.337 [0.305, 0.368] | 0.693 [0.629, 0.783] | 0.459 [0.456, 0.463] |

#### Path-persistency sweep

| Path persistency | OLSR | AODV | Static reference |
|---:|---:|---:|---:|
| 0.00 | 0.362 [0.330, 0.395] | 0.643 [0.523, 0.759] | 0.428 [0.421, 0.435] |
| 0.25 | 0.303 [0.246, 0.361] | 0.642 [0.596, 0.690] | 0.443 [0.434, 0.451] |
| 0.50 | 0.312 [0.274, 0.368] | 0.591 [0.524, 0.645] | 0.450 [0.448, 0.452] |
| 0.75 | 0.337 [0.305, 0.368] | 0.693 [0.629, 0.783] | 0.459 [0.456, 0.463] |
| 1.00 | 0.345 [0.283, 0.420] | 0.681 [0.627, 0.736] | 0.467 [0.467, 0.467] |

### Ladder topology

#### Path-life sweep

| Path life | OLSR | AODV | Static reference |
|---:|---:|---:|---:|
| 0.1 | 0.090 [0.063, 0.108] | 0.331 [0.311, 0.352] | 0.078 [0.074, 0.081] |
| 0.3 | 0.153 [0.115, 0.203] | 0.524 [0.460, 0.575] | 0.266 [0.261, 0.271] |
| 0.5 | 0.148 [0.140, 0.156] | 0.553 [0.515, 0.612] | 0.448 [0.441, 0.454] |
| 0.7 | 0.196 [0.153, 0.238] | 0.569 [0.347, 0.698] | 0.633 [0.625, 0.641] |
| 0.9 | 0.249 [0.206, 0.283] | 0.704 [0.466, 0.847] | 0.829 [0.819, 0.837] |

#### Stability sweep

| Stability | OLSR | AODV | Static reference |
|---:|---:|---:|---:|
| 0.0 | 0.191 [0.162, 0.220] | 0.497 [0.475, 0.516] | 0.368 [0.367, 0.369] |
| 0.2 | 0.184 [0.161, 0.220] | 0.490 [0.444, 0.543] | 0.389 [0.386, 0.392] |
| 0.4 | 0.179 [0.160, 0.202] | 0.509 [0.435, 0.562] | 0.409 [0.403, 0.413] |
| 0.6 | 0.177 [0.132, 0.221] | 0.476 [0.425, 0.534] | 0.428 [0.418, 0.435] |
| 0.8 | 0.148 [0.140, 0.156] | 0.553 [0.515, 0.613] | 0.448 [0.442, 0.454] |

#### Path-persistency sweep

| Path persistency | OLSR | AODV | Static reference |
|---:|---:|---:|---:|
| 0.00 | 0.159 [0.108, 0.225] | 0.454 [0.372, 0.519] | 0.388 [0.386, 0.390] |
| 0.25 | 0.158 [0.134, 0.186] | 0.526 [0.498, 0.567] | 0.413 [0.408, 0.418] |
| 0.50 | 0.169 [0.128, 0.208] | 0.511 [0.476, 0.571] | 0.429 [0.426, 0.433] |
| 0.75 | 0.148 [0.140, 0.156] | 0.553 [0.515, 0.613] | 0.448 [0.440, 0.454] |
| 1.00 | 0.140 [0.121, 0.156] | 0.570 [0.492, 0.672] | 0.466 [0.464, 0.467] |

## Descriptive observations and limitations

- Across all three topologies, higher requested path life gives higher measured S–R uptime as expected. PDR generally increases with path life, although the size and smoothness of the change differ by topology and routing variant.
- Stability sweeps do not show a common monotonic PDR response across topology/variant combinations. Path-persistency effects are also topology- and variant-dependent; several CIs overlap broadly, and five graph realizations provide limited precision.
- The static reference is useful for separating route-control behavior from the network/MAC/PHY/traffic ceiling, but it is not an idealized lossless oracle. Some static-reference intervals are degenerate because the outcomes were identical across the five realization means at that point.
- The experiment varies one generator control at a time; the requested stability and persistency controls are not claimed to be independent physical scalar properties. Consult measured DG-property records and plots alongside requested parameter values.
- Results apply to this 60-frame, 1 fps trace and traffic schedule. They do not establish behavior at other frame rates or topologies. DSDV was omitted, so no DSDV comparison or ranking is made.

## Reproduction

The campaign consisted of nine `run_pipeline-sweep.py` invocations, one for every topology × swept parameter pair. Each invocation used `--stages graph,dg,sim,plot`, `--sweep`, `--seed 42`, `--epoch 5`, `--trials 1000`, `--p-edge 0.5`, `--dg-frames 60`, `--fps 1.0`, topology length 3, S→R, `--routing olsr,aodv`, `--include-static-baseline`, `--warmup 45`, `--warmup-mode first`, `--link-down-loss-db 125`, and `--ns3-dir /home/hledirach/Documents/sp1-sp2`. Non-swept DG controls were path life 0.5, stability 0.8, and persistency 0.75. Sweep increments were 0.2 for path life, 0.2 for stability, and 0.25 for path persistency. Each invocation used its corresponding output path under `simple-graph-experiments-v2/phase5/<topology>/<parameter>/`.

## Artifacts

Each cell directory below contains `plots/summary.csv`, `plots/aggregate.csv`, measured `plots/dg_properties_summary.csv` and PNG plots, serialized DG frames and properties, per-epoch replay CSVs/configs, and the cell-level `config.json`.

- [Phase 5 campaign log](../simple-graph-experiments-v2/phase5/campaign.log)
- [Line / path life aggregate](../simple-graph-experiments-v2/phase5/line/path_life/plots/aggregate.csv) · [summary](../simple-graph-experiments-v2/phase5/line/path_life/plots/summary.csv) · [DG properties](../simple-graph-experiments-v2/phase5/line/path_life/plots/dg_properties_summary.csv) · [PDR plot](../simple-graph-experiments-v2/phase5/line/path_life/plots/PDR_lifetime.png)
- [Line / stability aggregate](../simple-graph-experiments-v2/phase5/line/stability/plots/aggregate.csv) · [summary](../simple-graph-experiments-v2/phase5/line/stability/plots/summary.csv) · [DG properties](../simple-graph-experiments-v2/phase5/line/stability/plots/dg_properties_summary.csv) · [PDR plot](../simple-graph-experiments-v2/phase5/line/stability/plots/PDR_stab.png)
- [Line / path persistency aggregate](../simple-graph-experiments-v2/phase5/line/pathPersistency/plots/aggregate.csv) · [summary](../simple-graph-experiments-v2/phase5/line/pathPersistency/plots/summary.csv) · [DG properties](../simple-graph-experiments-v2/phase5/line/pathPersistency/plots/dg_properties_summary.csv) · [PDR plot](../simple-graph-experiments-v2/phase5/line/pathPersistency/plots/PDR_persist.png)
- [Two-lines / path life aggregate](../simple-graph-experiments-v2/phase5/two-lines/path_life/plots/aggregate.csv) · [summary](../simple-graph-experiments-v2/phase5/two-lines/path_life/plots/summary.csv) · [DG properties](../simple-graph-experiments-v2/phase5/two-lines/path_life/plots/dg_properties_summary.csv) · [PDR plot](../simple-graph-experiments-v2/phase5/two-lines/path_life/plots/PDR_lifetime.png)
- [Two-lines / stability aggregate](../simple-graph-experiments-v2/phase5/two-lines/stability/plots/aggregate.csv) · [summary](../simple-graph-experiments-v2/phase5/two-lines/stability/plots/summary.csv) · [DG properties](../simple-graph-experiments-v2/phase5/two-lines/stability/plots/dg_properties_summary.csv) · [PDR plot](../simple-graph-experiments-v2/phase5/two-lines/stability/plots/PDR_stab.png)
- [Two-lines / path persistency aggregate](../simple-graph-experiments-v2/phase5/two-lines/pathPersistency/plots/aggregate.csv) · [summary](../simple-graph-experiments-v2/phase5/two-lines/pathPersistency/plots/summary.csv) · [DG properties](../simple-graph-experiments-v2/phase5/two-lines/pathPersistency/plots/dg_properties_summary.csv) · [PDR plot](../simple-graph-experiments-v2/phase5/two-lines/pathPersistency/plots/PDR_persist.png)
- [Ladder / path life aggregate](../simple-graph-experiments-v2/phase5/ladder/path_life/plots/aggregate.csv) · [summary](../simple-graph-experiments-v2/phase5/ladder/path_life/plots/summary.csv) · [DG properties](../simple-graph-experiments-v2/phase5/ladder/path_life/plots/dg_properties_summary.csv) · [PDR plot](../simple-graph-experiments-v2/phase5/ladder/path_life/plots/PDR_lifetime.png)
- [Ladder / stability aggregate](../simple-graph-experiments-v2/phase5/ladder/stability/plots/aggregate.csv) · [summary](../simple-graph-experiments-v2/phase5/ladder/stability/plots/summary.csv) · [DG properties](../simple-graph-experiments-v2/phase5/ladder/stability/plots/dg_properties_summary.csv) · [PDR plot](../simple-graph-experiments-v2/phase5/ladder/stability/plots/PDR_stab.png)
- [Ladder / path persistency aggregate](../simple-graph-experiments-v2/phase5/ladder/pathPersistency/plots/aggregate.csv) · [summary](../simple-graph-experiments-v2/phase5/ladder/pathPersistency/plots/summary.csv) · [DG properties](../simple-graph-experiments-v2/phase5/ladder/pathPersistency/plots/dg_properties_summary.csv) · [PDR plot](../simple-graph-experiments-v2/phase5/ladder/pathPersistency/plots/PDR_persist.png)

Phase 5 is complete. No Phase 6 experiments were started; the campaign is paused at the phase boundary for approval.
