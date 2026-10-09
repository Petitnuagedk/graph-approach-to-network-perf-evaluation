# Phase 2 report: replay metrics and trace oracle

## Scope and changes

Phase 2 instrumentation is implemented. No Phase 3–6 experiments were started. The existing `simple-graph-experiments/` campaign was not modified. A single deterministic verification case was used rather than a multi-realization campaign.

- `sp1-sp2/scratch/graph-run.cc`
  - PDR offered-packet denominator now comes from the `UdpClient::Tx` trace, before IPv4 routing can drop packets.
  - v2 link-down loss is 125 dB, below the 150 dB TMLM sparse threshold so it is stored rather than replaced by the default loss. With the scenario's 20 dBm Tx and −101 dBm receive sensitivity, this is below the receive threshold while reducing the interpolation transition window.
  - Warm-up topology defaults to `first`; direct pipeline calls default to 0 s for legacy behavior, while the v2 campaign runner passes 45 s by default, rounded up to whole frames. The Phase 2 validation explicitly passed `--warmup 45`.
  - Trace-derived per-run S–R uptime, up-run statistics and full list, transition count, alternative-path-gated path-identity retention, full outage list, per-outage re-establishment time and aligned outage duration are written in each replay row. Re-establishment is NaN when no packet is delivered before the next break or trace end.
  - An oracle-path static-routing variant can be selected with `--include-static-baseline` in the pipeline or `static` in `--routing`.
  - Control Tx packets and bytes are counted at IPv4 Tx and classified as OLSR HELLO/TC/MID/HNA, AODV HELLO/RREQ/RREP/RERR/RREP-ACK, or DSDV update. Control bytes are IPv4 packet sizes; ratios per delivered data packet are also emitted.
  - Direct ns-3 replays write `config.json`; the pipeline writes/overwrites detailed configs beside the work root, each DG, and each epoch, including args, seeds, timestamps, source revision/hash, and ns-3 revision/version if available.
- `run_pipeline-sweep.py`: direct calls retain the legacy 0 s warm-up default; the v2 campaign runner passes 45 s and frame-0 warm-up topology by default. The v2 pipeline/campaign runner use 125 dB down loss; `--include-static-baseline` adds the oracle-route baseline. DG requested settings are stored with properties, and measurements are read back from the serialized trace sent to ns-3.
- `run_simple_graph_experiments.py`: defaults to the new `simple-graph-experiments-v2/` output root and forwards the v2 settings.
- `plot.py`: replay epochs are averaged within each graph realization; means and deterministic percentile-bootstrap 95% CIs are computed over realizations. It plots routing efficiency and control packet/byte overhead per delivered packet.
- `oracle_metrics.py`, `tests/test_oracle_metrics.py`, `tests/test_plot_aggregation.py`: reference metrics and tests for known trace values and epoch-within-realization aggregation.
- `README.md`: v2 flags and reproduction command added.

## Exact verification run

Work root: `simple-graph-experiments-v2/phase2/final/`

```bash
python run_pipeline-sweep.py \
  --work-dir simple-graph-experiments-v2/phase2/final \
  --stages graph,dg,sim,plot \
  --topology ladder --topology-length 3 --pair-a S --pair-b R \
  --trials 1000 --dg-frames 60 --path-life 0.9 --stability 0.8 \
  --path-persistency 0.75 --epoch 1 --seed 42 \
  --warmup 45 --warmup-mode first --link-down-loss-db 125 \
  --include-static-baseline --ns3-dir /home/hledirach/Documents/sp1-sp2
```

Design and row-count check: 1 generated DG × 1 replay epoch × 4 variants (OLSR, AODV, DSDV, static) = **4 replay rows**, verified in both replay CSV and `plots/summary.csv`; `plots/aggregate.csv` has 4 protocol aggregates. Same serialized trace and seed 42 were supplied to all four variants.

Requested generator settings: path_life 0.9, stability 0.8, persistency 0.75. Serialized-trace measurements: S–R uptime 0.9 (54/60 frames), mean up-run 7.714 s, median 8 s, p90 8 s, up-run list [8, 8, 8, 8, 8, 7, 7] s, 12 connectivity transitions, six 1 s outages, 8 distinct shortest routes, path-identity retention 0.744681. The measured uptime matches path_life 0.9. Stability and persistency remain requested generator controls rather than independent scalar output measurements.

The original generator-side property calculation produced route retention 0.851064 / 7 route changes, whereas a fresh measurement from the serialized trace produced 0.744681 / 12. This exposed a discrepancy between pre-export graphs and the exact trace sent to ns-3. The pipeline now measures DG properties from the serialized `frames.csv`; the C++ replay oracle and independent Python recomputation agree at 0.744681 / 12.

### Per-protocol validation values

All protocols offered 360 application packets. These are one-seed instrumentation checks, **not protocol rankings**.

| Variant | Delivered | PDR | Oracle uptime | Routing efficiency | Control packets | Control bytes | Control packets / delivered | Control bytes / delivered |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| OLSR | 127 | 0.352778 | 0.900000 | 0.391975 | 577 | 43,088 | 4.543307 | 339.275591 |
| AODV | 255 | 0.708333 | 0.900000 | 0.787037 | 1,163 | 55,468 | 4.560784 | 217.521569 |
| DSDV | 112 | 0.311111 | 0.900000 | 0.345679 | 346 | 21,904 | 3.089286 | 195.571429 |
| Static oracle route | 299 | 0.830556 | 0.900000 | 0.922840 | 0 | 0 | 0 | 0 |

Subtype counts are in the replay CSV. OLSR: 351 HELLO, 226 TC. AODV: 766 HELLO, 122 RREQ, 156 RREP, 109 RERR, 10 RREP-ACK. DSDV: 346 updates. Static: no routing control packets.

The static-route reference achieved PDR 0.830556 rather than the oracle uptime 0.9. It is the measured protocol-free oracle-path baseline under this Wi-Fi/packet schedule, not a mathematical guarantee of one delivery per up-frame. No routing ranking is inferred from these one-seed numbers. The DSDV static-network issue already noted in Phase 1 was not investigated further, per instruction; DSDV must not be ranked until that known convergence issue is addressed.

**Retrospective interpretation note (2026-10-08):** `routing_efficiency = PDR / oracle uptime` is retained here only as a historical descriptive quotient and is **not interpretable as an efficiency, probability, normalized score, upper/lower bound, or delivery ceiling**. Later Phase 7B channel validation showed that packets offered in a down frame may be delivered in a later up frame, yielding PDR/oracle-uptime ratios above 1; Phase 6 observed ratios below 1. Neither direction is a bound or a calibrated interpretation. Do not use this quotient for ranking, normalization, or claims about delivery relative to a channel ceiling. The underlying PDR and oracle-uptime measures remain reported separately with their original definitions.

Re-establishment lists in the CSV are aligned one-to-one with the six oracle outages. Finite entries give seconds from oracle link-up to first received packet; `nan` means no packet arrived during the succeeding up interval. This explains every re-establishment NaN in this case. The case has no zero PDR and no other NaN metric.

## Artifacts

- Replay rows and full metric lists: [trace_replay_results.csv](../simple-graph-experiments-v2/phase2/final/ns3-results/graph_0001__dg/epoch_0001/trace_replay_results.csv)
- Per-epoch configuration: [config.json](../simple-graph-experiments-v2/phase2/final/ns3-results/graph_0001__dg/epoch_0001/config.json)
- Raw summary: [summary.csv](../simple-graph-experiments-v2/phase2/final/plots/summary.csv)
- Realization-level bootstrap aggregates: [aggregate.csv](../simple-graph-experiments-v2/phase2/final/plots/aggregate.csv)
- Requested/measured DG properties: [properties.csv](../simple-graph-experiments-v2/phase2/final/dynamic_frames/graph_0001/properties.csv)
- Plots: [PDR](../simple-graph-experiments-v2/phase2/final/plots/PDR_run.png), [routing efficiency](../simple-graph-experiments-v2/phase2/final/plots/ROUTING_EFFICIENCY_run.png), [control packets per delivered](../simple-graph-experiments-v2/phase2/final/plots/CONTROL_PACKETS_PER_DELIVERED_run.png), [control bytes per delivered](../simple-graph-experiments-v2/phase2/final/plots/CONTROL_BYTES_PER_DELIVERED_run.png), [oracle uptime](../simple-graph-experiments-v2/phase2/final/plots/ORACLE_UPTIME_run.png), [oracle up-run duration](../simple-graph-experiments-v2/phase2/final/plots/ORACLE_UP_RUN_run.png).

Because this smoke design has only one realization, its bootstrap intervals have zero width. The aggregation unit test uses three epochs across two realizations and verifies epoch averaging precedes the bootstrap.

## Verification completed

- ns-3 3.46.1 scenario built successfully.
- `tests/test_oracle_metrics.py`: 2 tests passed, including the hand-built trace with known uptime, runs, transitions, alternative paths, and outage duration.
- `tests/test_plot_aggregation.py`: passed; checks 2 epochs are averaged within realization before the across-realization mean/CI.
- Python compilation passed for changed Python modules.
- Same-seed rerun produced identical CSV metrics and lists (excluding nondeterministic wall/cpu timing columns).
- Config JSON parsed successfully at work-root, DG, and epoch levels. J2 revision is recorded; ns-3 commit is null because the ns-3 directory is not a git repository; version 3.46.1 is recorded.
- Plotter wrote 9 PNGs; raw and aggregate CSV row counts match the design.
- No existing campaign outputs were modified. No broad campaign (>20 ns-3 runs) was launched.

## Remaining limitations

- The verification set is one realization and one replay epoch; CI intervals are intentionally degenerate. No statistical claim or protocol ordering follows.
- Static baseline is measured with the same MAC/PHY; it is not an ideal channel with guaranteed delivery.
- DSDV's static-trace convergence/outage issue is still known and unresolved, as requested.
