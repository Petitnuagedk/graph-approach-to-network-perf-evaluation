# A4.2 — fixed 120-s warm-up load sweep

**Written after prelaunch audit; no A4.2 simulator variants were launched.** The frozen preregistration requires a complete runtime projection at or below 24 hours before the first run. The projection is not estimable from the registered baseline inputs, so the mandatory stop gate failed closed.

Preregistration SHA-256: `5ab4e85f5b335afabe89147e30e445bf409429c3bb8353876607719bfa5bae06`. G0 PASS: source `FRAME_RATE=1.0`, so one frame is one second. The 90-cell grid was planned but 0/90 variants were attempted or charged; Alpha accounting remains 70/300.

Missing projection inputs: only 3 A4.0A pilot records have successful status. A4.0A successful pilots are: aodv phi1 (662.068669 s), dsdv phi1 (869.164999 s), dsdv phi10 (2284.32516 s). The registered 1%-to-10% per-protocol interpolation requires successful phi1 and phi10 pilot times for both AODV and OLSR. Those pairs are incomplete, making all 90 per-run projections unavailable; no substitute model or pilot was introduced.

No resource-guard launch check was needed because the projection gate stopped the campaign before any simulator invocation. There were no timeouts, retries, readiness observations, or PDR measurements.

## Planned status

All 90 planned combinations are marked `not_attempted_projection_gate` in [planned_cells.csv](planned_cells.csv). The complete per-run table is intentionally empty: [per_run.csv](per_run.csv).

| Protocol | N | Load | Family cells | Readiness misses |
|---|---:|---:|---:|---:|
| aodv | 42 | phi1 | 5 | not measured |
| aodv | 42 | phi5 | 5 | not measured |
| aodv | 42 | phi10 | 5 | not measured |
| aodv | 92 | phi1 | 5 | not measured |
| aodv | 92 | phi5 | 5 | not measured |
| aodv | 92 | phi10 | 5 | not measured |
| aodv | 162 | phi1 | 5 | not measured |
| aodv | 162 | phi5 | 5 | not measured |
| aodv | 162 | phi10 | 5 | not measured |
| olsr | 42 | phi1 | 5 | not measured |
| olsr | 42 | phi5 | 5 | not measured |
| olsr | 42 | phi10 | 5 | not measured |
| olsr | 92 | phi1 | 5 | not measured |
| olsr | 92 | phi5 | 5 | not measured |
| olsr | 92 | phi10 | 5 | not measured |
| olsr | 162 | phi1 | 5 | not measured |
| olsr | 162 | phi5 | 5 | not measured |
| olsr | 162 | phi10 | 5 | not measured |

All status-matrix cells and operating candidates are unmeasured, not failures: [status_matrix.csv](status_matrix.csv), [operating_candidates.csv](operating_candidates.csv). No routing, readiness, or load verdict is drawn.

## Decision and stop

The missing A4.0A OLSR baselines and AODV phi10 baseline prevent demonstrating that the planned campaign is within the preregistered 24-hour ceiling. Stop before launch; this does not claim that actual runtime would exceed 24 hours. A revised projection method or new pilot requires a separately registered/user-authorized disposition before any A4.2 run.

DSDV remains excluded by user direction, not a measured routing verdict; rationale placeholder: `[user to state]`. No A4.3, detector/warm-up change, 2% run, or DSDV reinstatement.
