# Phase 3 report: temporal-scale / rho pilot

## Scope

The Phase 0 audit recommended making the ratio of mean S–R up-run duration to protocol timers an explicit axis. This bounded pilot varies only replay frame rate (`fps`) while reusing the exact Phase 2 serialized 60-frame DG trace. This holds the topology sequence, requested DG properties, graph realization, seed, PHY, traffic rate, warm-up, and loss settings fixed while changing the physical duration of each trace frame.

This is a **one-realization pilot**, not the full inferential campaign and not a protocol ranking. The user-requested DSDV investigation remains out of scope; DSDV rows are retained for completeness but excluded from ranking because its known convergence issue remains unresolved.

## Design and run count

- Trace: Phase 2 ladder DG, S→R, requested path_life 0.9, stability 0.8, persistency 0.75; 60 source frames. SHA-256: `ef869d757857c33cf78d43844fa7581fddb2641410c5b10f77aff5125e9d24fe`.
- Replay scale: 0.5, 1.0, and 2.0 frames/s. These produce 118 s, 59 s, and 29.5 s of trace time respectively; each replay used a 45 s frame-0 warm-up (rounded to 23, 45, and 90 frames respectively).
- Same ns-3 seed 42 and trace across scales; same 50 kbps, 1024-byte UDP flow, 20 dBm, 802.11g ad-hoc, interpolation on, 125 dB down-loss, and 150 dB sparse threshold.
- Variants: OLSR, AODV, DSDV, static oracle-route baseline.
- Run count: 3 fps values × 1 DG realization × 1 replay epoch × 4 variants = **12 ns-3 variant runs**. Every point produced four rows in its replay CSV and `summary.csv`, four aggregates, and nine plots.

The mean up-run in seconds is computed from the identical run-length sequence in frames divided by fps. The resulting $\rho = \text{mean up-run duration}/\text{timer}$ values show that this scale range crosses the OLSR TC interval and moves DSDV's ratio around its 15-second periodic update.

| fps (frames/s) | Mean S–R up-run (s) | OLSR Hello 2 s | OLSR TC 5 s | OLSR neighbor hold 6 s | AODV Hello 1 s | AODV active timeout 3 s | DSDV periodic 15 s | DSDV hold 45 s |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.5 | 15.429 | 7.714 | 3.086 | 2.571 | 15.429 | 5.143 | 1.029 | 0.343 |
| 1.0 | 7.714 | 3.857 | 1.543 | 1.286 | 7.714 | 2.571 | 0.514 | 0.171 |
| 2.0 | 3.857 | 1.929 | 0.771 | 0.643 | 3.857 | 1.286 | 0.257 | 0.086 |

## Results

PDR and delivered packet counts are per one replay realization. The static route is a measured Wi-Fi reference, not a guaranteed-delivery ideal channel.

| fps | Variant | Offered | Delivered | PDR | Oracle uptime | PDR / uptime | Control packets / delivered |
|---:|---|---:|---:|---:|---:|---:|---:|
| 0.5 | OLSR | 720 | 272 | 0.377778 | 0.900000 | 0.419753 | 3.488971 |
| 0.5 | AODV | 720 | 663 | 0.920833 | 0.900000 | 1.023148 | 2.520362 |
| 0.5 | DSDV | 720 | 208 | 0.288889 | 0.900000 | 0.320988 | 2.682692 |
| 0.5 | Static oracle route | 720 | 602 | 0.836111 | 0.900000 | 0.929012 | 0 |
| 1.0 | OLSR | 360 | 127 | 0.352778 | 0.900000 | 0.391975 | 4.543307 |
| 1.0 | AODV | 360 | 255 | 0.708333 | 0.900000 | 0.787037 | 4.560784 |
| 1.0 | DSDV | 360 | 112 | 0.311111 | 0.900000 | 0.345679 | 3.089286 |
| 1.0 | Static oracle route | 360 | 299 | 0.830556 | 0.900000 | 0.922840 | 0 |
| 2.0 | OLSR | 180 | 35 | 0.194444 | 0.900000 | 0.216049 | 11.714286 |
| 2.0 | AODV | 180 | 155 | 0.861111 | 0.900000 | 0.956790 | 5.812903 |
| 2.0 | DSDV | 180 | 36 | 0.200000 | 0.900000 | 0.222222 | 6.416667 |
| 2.0 | Static oracle route | 180 | 150 | 0.833333 | 0.900000 | 0.925926 | 0 |

### Interpretation and cautions

- OLSR's measured PDR decreases from 0.378 at 0.5 fps to 0.194 at 2 fps as mean up-run / OLSR TC falls from 3.09 to 0.77. This is consistent with a sensitivity to route-maintenance timescales, but one trace is insufficient to establish a general effect.
- AODV's measured PDR is 0.709 at 1 fps and higher at both other scales in this trace. This single sequence is not monotone in fps; multi-realization replication is required before interpreting a trend.
- Static-route PDR remains approximately 0.83 across the three scales, providing a useful check on the same MAC/PHY replay. It is slightly below oracle uptime and should not be read as an ideal connectivity bound.
- At 0.5 fps, AODV PDR exceeds frame-count oracle uptime (0.921 vs 0.900). PDR is packet-sampled while oracle uptime is a frame-duration fraction. **Retrospective interpretation note (2026-10-08):** the quotient `routing_efficiency = PDR / oracle uptime` is non-interpretable as an efficiency, probability, normalized score, or bound. Phase 7B showed that packets sent during down frames may buffer and arrive in later up frames, producing ratios above 1; Phase 6 also observed values below 1. Neither side is a delivery bound or meaningful normalization. Preserve the value only as a historical descriptive quotient; do not rank, normalize, or infer a ceiling from it.
- No PDR is zero. Re-establishment lists contain `nan` entries only when no delivery occurred before the following outage/trace boundary; scalar metric fields have no unexplained NaNs.
- DSDV values are included as raw observations only. Its convergence issue remains unresolved and DSDV is not compared or ranked.
- Each scale has one realization and one replay epoch, so bootstrap intervals are degenerate. These numbers are diagnostic and support no inferential claim.

## Artifacts

- 0.5 fps replay CSV: [trace_replay_results.csv](../simple-graph-experiments-v2/phase3/rho_fps_0p5/ns3-results/graph_0001/epoch_0001/trace_replay_results.csv); [config.json](../simple-graph-experiments-v2/phase3/rho_fps_0p5/ns3-results/graph_0001/epoch_0001/config.json); [PDR plot](../simple-graph-experiments-v2/phase3/rho_fps_0p5/plots/PDR_graph.png)
- 1.0 fps replay CSV: [trace_replay_results.csv](../simple-graph-experiments-v2/phase3/rho_fps_1p0/ns3-results/graph_0001/epoch_0001/trace_replay_results.csv); [config.json](../simple-graph-experiments-v2/phase3/rho_fps_1p0/ns3-results/graph_0001/epoch_0001/config.json); [PDR plot](../simple-graph-experiments-v2/phase3/rho_fps_1p0/plots/PDR_graph.png)
- 2.0 fps replay CSV: [trace_replay_results.csv](../simple-graph-experiments-v2/phase3/rho_fps_2p0/ns3-results/graph_0001/epoch_0001/trace_replay_results.csv); [config.json](../simple-graph-experiments-v2/phase3/rho_fps_2p0/ns3-results/graph_0001/epoch_0001/config.json); [PDR plot](../simple-graph-experiments-v2/phase3/rho_fps_2p0/plots/PDR_graph.png)
- Source DG properties: [properties.csv](../simple-graph-experiments-v2/phase2/final/dynamic_frames/graph_0001/properties.csv)

The phase2 source trace was reused read-only; the previous campaign root remains unchanged. Each Phase 3 run config records ns-3 3.46.1, seed 42, fps, warm-up settings, source hashes, and timestamp. No Phase 4 experiments were started.

## Reproduction

From the J2 workspace, use the existing Phase 2 graph/DG outputs and run once per fps value:

```bash
python run_pipeline-sweep.py \
  --work-dir simple-graph-experiments-v2/phase3/rho_fps_0p5 \
  --graph-csv simple-graph-experiments-v2/phase2/final/graph.csv \
  --dg-csv simple-graph-experiments-v2/phase2/final/dynamic_frames \
  --stages sim,plot --topology ladder --topology-length 3 \
  --pair-a S --pair-b R --epoch 1 --seed 42 --fps 0.5 \
  --routing all --warmup 45 --warmup-mode first \
  --link-down-loss-db 125 --include-static-baseline \
  --ns3-dir /home/hledirach/Documents/sp1-sp2
```

Change the fps value and work directory for the other two points. Phase 3 is now paused pending approval before proceeding beyond this rho pilot.
