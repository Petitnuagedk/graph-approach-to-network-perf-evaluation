# Phase 4 report: replicated temporal-scale / rho campaign

## Scope and design

Phase 4 expands the Phase 3 single-trace rho pilot into a paired multi-realization comparison. It uses the same ladder topology and requested DG settings but generates five independent DG realizations, then replays each trace with five ns-3 seeds at each temporal scale. The DSDV variant is deliberately omitted, per the instruction not to spend campaign time investigating its unresolved convergence issue. A static oracle-route reference is retained.

- Topology and flow: ladder, length 3, S→R; path_life 0.9, stability 0.8, path persistency 0.75; 60 frames per DG.
- Temporal scales: 0.5, 1.0, and 2.0 frames/s. Mean S–R up-run is 7.714 frames, corresponding to 15.429, 7.714, and 3.857 seconds.
- Replay settings: seed base 42, 45 s `first`-frame warm-up, 125 dB down loss, interpolation enabled, 50 kbps, 1024-byte packets, 802.11g ad-hoc, 20 dBm.
- Variants: OLSR, AODV, and the static oracle-route reference.
- Run count: 3 scales × 5 independent DG realizations × 5 replay epochs × 3 variants = **225 replay variants**. Each scale has 75 rows in `summary.csv` (25 samples per variant), 3 aggregate rows, 25 epoch CSVs, 31 configuration JSONs, and 9 plots.

All five serialized frame traces are byte-identical across the three scales by DG seed, so fps comparisons are paired by realization. (The link-state sequence is also held fixed between Phase 3 and Phase 4.) The full 60-frame trace duration changes with fps: 118 s, 59 s, and 29.5 s. This is a temporal-scale test, not a fixed-duration test; the finite traffic window therefore differs across the three rates.

The ratio $\rho = \text{mean up-run duration}/\text{protocol timer}$ is:

| fps | Mean up-run (s) | OLSR Hello (2 s) | OLSR TC (5 s) | OLSR neighbor hold (6 s) | AODV Hello (1 s) | AODV active timeout (3 s) |
|---:|---:|---:|---:|---:|---:|---:|
| 0.5 | 15.429 | 7.714 | 3.086 | 2.571 | 15.429 | 5.143 |
| 1.0 | 7.714 | 3.857 | 1.543 | 1.286 | 7.714 | 2.571 |
| 2.0 | 3.857 | 1.929 | 0.771 | 0.643 | 3.857 | 1.286 |

## Results

Table entries are mean PDR over five graph-realization means, with population standard deviation and deterministic percentile-bootstrap 95% CI. Replay epochs were averaged within each DG realization before computing between-realization statistics. `n_realizations=5`, `n_epochs=25` per protocol and scale.

| fps | Variant | Mean PDR | SD | Bootstrap 95% CI | Mean control packets / delivered |
|---:|---|---:|---:|---:|---:|
| 0.5 | OLSR | 0.2666 | 0.0627 | [0.2142, 0.3190] | 5.3947 |
| 0.5 | AODV | 0.7569 | 0.2695 | [0.4872, 0.9089] | 4.1801 |
| 0.5 | Static oracle route | 0.8333 | 0.0090 | [0.8249, 0.8408] | 0 |
| 1.0 | OLSR | 0.2490 | 0.0441 | [0.2058, 0.2827] | 6.8686 |
| 1.0 | AODV | 0.7039 | 0.2367 | [0.4660, 0.8477] | 5.9385 |
| 1.0 | Static oracle route | 0.8291 | 0.0109 | [0.8186, 0.8366] | 0 |
| 2.0 | OLSR | 0.2504 | 0.0397 | [0.2169, 0.2856] | 9.3420 |
| 2.0 | AODV | 0.7660 | 0.0506 | [0.7187, 0.8024] | 6.8332 |
| 2.0 | Static oracle route | 0.8307 | 0.0076 | [0.8244, 0.8369] | 0 |

### Interpretation

**Retrospective interpretation note (2026-10-08):** any plotted or stored `routing_efficiency = PDR / oracle uptime` quotient in this phase is non-interpretable as an efficiency, probability, normalized score, bound, or delivery ceiling. Phase 7B showed that packets offered during a down frame can be buffered and received later during an up frame, permitting ratios above 1; Phase 6 also observed ratios below 1. Neither direction is a bound or a basis for normalization/ranking. Keep historical values only as descriptive quotients and interpret PDR and oracle uptime separately.

- The pronounced OLSR decline at 2 fps in the Phase 3 single-trace pilot did **not** reproduce in this paired multi-realization campaign: mean PDR is 0.2666, 0.2490, and 0.2504 across increasing fps. The confidence intervals overlap substantially; this run does not support a strong monotonic frame-rate effect for OLSR over these points.
- AODV also has no monotonic trend: means are 0.7569, 0.7039, and 0.7660. Its variability is especially large at 0.5 and 1 fps, reflected by wide intervals. The AODV PDR interval at 2 fps is narrower in this five-realization sample, not proof of generally lower variability.
- Static-reference PDR stays near 0.83 at all three fps values, with comparatively narrow intervals. This suggests that the measured variation in the routing protocols is not simply a gross change in the link trace, while remaining subject to packet sampling and MAC/PHY effects.
- The increase in control packets per delivered packet with fps is visible for both dynamic protocols. It is descriptive and should be interpreted alongside the different observation durations and delivered-packet counts.
- These are cross-scale observations, not a protocol ranking. DSDV was excluded because its convergence problem remains unresolved. No DSDV result was generated or ranked in Phase 4.
- There were no zero-PDR rows and no unexplained scalar NaNs. Re-establishment-time list entries may be NaN when a route did not recover before the next outage/trace boundary.

## Reproduction

Run once for each of `fps=0.5`, `fps=1.0`, and `fps=2.0`, changing the work directory suffix accordingly:

```bash
python run_pipeline-sweep.py \
  --work-dir simple-graph-experiments-v2/phase4/rho_fps_0p5 \
  --stages graph,dg,sim,plot \
  --topology ladder --topology-length 3 --pair-a S --pair-b R \
  --trials 1000 --dg-frames 60 --path-life 0.9 --stability 0.8 \
  --path-persistency 0.75 --epoch 5 --seed 42 --fps 0.5 \
  --routing olsr,aodv --warmup 45 --warmup-mode first \
  --link-down-loss-db 125 --include-static-baseline \
  --ns3-dir /home/hledirach/Documents/sp1-sp2
```

## Artifacts

- 0.5 fps aggregates: [aggregate.csv](../simple-graph-experiments-v2/phase4/rho_fps_0p5/plots/aggregate.csv); [summary.csv](../simple-graph-experiments-v2/phase4/rho_fps_0p5/plots/summary.csv); [PDR plot](../simple-graph-experiments-v2/phase4/rho_fps_0p5/plots/PDR_run.png)
- 1.0 fps aggregates: [aggregate.csv](../simple-graph-experiments-v2/phase4/rho_fps_1p0/plots/aggregate.csv); [summary.csv](../simple-graph-experiments-v2/phase4/rho_fps_1p0/plots/summary.csv); [PDR plot](../simple-graph-experiments-v2/phase4/rho_fps_1p0/plots/PDR_run.png)
- 2.0 fps aggregates: [aggregate.csv](../simple-graph-experiments-v2/phase4/rho_fps_2p0/plots/aggregate.csv); [summary.csv](../simple-graph-experiments-v2/phase4/rho_fps_2p0/plots/summary.csv); [PDR plot](../simple-graph-experiments-v2/phase4/rho_fps_2p0/plots/PDR_run.png)

The existing `simple-graph-experiments/` campaign and the Phase 2/3 outputs were not modified. Phase 4 is complete; Phase 5 has not started and is paused for approval.
