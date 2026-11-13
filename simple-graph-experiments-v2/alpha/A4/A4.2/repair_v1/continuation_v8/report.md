# A4.2 — fixed 120-s warm-up load sweep

**Written after A4.2 results.** 90 planned AODV/OLSR variants; no DSDV. DSDV removal is user-directed (not a measured verdict); rationale: `[user to state]`. Phase 6D DSDV outage question not tested. No A4.0*/A4.1/A4.1b/A4.1c artifacts edited.

Prereg SHA-256 `d67aea893314e150ac06e7db2df2bcfc89f4ad8a6203f2a959e7d1411fa57450`; source [A4 runner](../a4.py#L27) defines 1 frame=1 s. G0 PASS. Fixed 120 warm-up frames +120 measurement frames; 240 frames total, simulation stop at t=239 s per A3 source last-frame stop convention.

**Gate/attempt summary:** G0 PASS; attempted 90/90, 0 unsuccessful/malformed/timeout. Budget 70+90=160/300. Readiness misses: 90/90 flags; misses never gated a launch. All 90 grid cells and detailed per-run metrics: [per_run.csv](per_run.csv). Window-only per-flow denominator/counters: [per_flow_post_readiness.csv](per_flow_post_readiness.csv).

## Per-run results

The complete 90-row per-run dataset contains full-window and post-readiness PDR, delay, control/load distribution, retry/collision diagnostics, wall/CPU time and attribution: [per_run.csv](per_run.csv). Scheduled-packet denominators and per-flow post-readiness counters are in [per_flow_post_readiness.csv](per_flow_post_readiness.csv). MAC/PHY counts are whole-run, including warm-up.

## Misses

The denominator is the five family cells per protocol×N×load; undefined readiness is separate.

| Protocol | N | Load | Flagged / 5 | >120 s / 5 | Undefined |
|---|---:|---|---:|---:|---:|
| aodv | 42 | phi1 | 5/5 | 4/5 | 1 |
| aodv | 42 | phi5 | 5/5 | 5/5 | 0 |
| aodv | 42 | phi10 | 5/5 | 4/5 | 1 |
| aodv | 92 | phi1 | 5/5 | 5/5 | 0 |
| aodv | 92 | phi5 | 5/5 | 0/5 | 5 |
| aodv | 92 | phi10 | 5/5 | 0/5 | 5 |
| aodv | 162 | phi1 | 5/5 | 3/5 | 2 |
| aodv | 162 | phi5 | 5/5 | 0/5 | 5 |
| aodv | 162 | phi10 | 5/5 | 0/5 | 5 |
| olsr | 42 | phi1 | 5/5 | 5/5 | 0 |
| olsr | 42 | phi5 | 5/5 | 5/5 | 0 |
| olsr | 42 | phi10 | 5/5 | 3/5 | 2 |
| olsr | 92 | phi1 | 5/5 | 4/5 | 1 |
| olsr | 92 | phi5 | 5/5 | 0/5 | 5 |
| olsr | 92 | phi10 | 5/5 | 0/5 | 5 |
| olsr | 162 | phi1 | 5/5 | 2/5 | 3 |
| olsr | 162 | phi5 | 5/5 | 0/5 | 5 |
| olsr | 162 | phi10 | 5/5 | 0/5 | 5 |

All 30 family×size×protocol statuses, including `pass`, `fail` with cause or `flagged-transient`, and per-cell highest tested passing load: [status_matrix.csv](status_matrix.csv). No untested 2% is inferred.

## Operating candidates

The per-size common candidate is the highest tested load passed by every family×protocol cell passing at 1%; `none` means no common tested level.

| N | Lowest-load passing family×protocol cells | Common candidate |
|---:|---:|---|
| 42 | 8 | phi1 (0.01) |
| 92 | 4 | phi1 (0.01) |
| 162 | 1 | phi1 (0.01) |

## Interpretation and stop

A flagged run’s PDR shortfall is classified convergence-affected unless an unflagged shortfall exists at the same protocol×N×phi; otherwise load effects are labeled transient-affected, not routing/MAC. Unflagged MAC attribution requires the registered ratio/rate thresholds versus the same max-degree node’s phi=1% baseline. Collision counters have no event timestamps; reported as whole-run. No ranking or ceiling inference.

Proposal only: A4.3 would need matched readiness and per-flow PDR windows (including after-readiness denominators), unflagged same-load comparators, and fixed-window PDR in independent graph realizations. Miss-affected cells are not clean load-effect estimates. No A4.3 run here.

**STOP.** No detector/warm-up change, 2% run, DSDV reinstatement, A4.3, or further cell disposition. See [Alpha limitations](../../LIMITATIONS.md).
