# A4.1 — convergence, delivery gaps, and warm-up

**Status: A4.1 execution complete; later stages not authorized.** All 45 registered family × N × protocol variants were attempted once and succeeded (45/45; no retries, failures, assertions, or timeouts). Execution was serial. A4.0's unresolved pilot failures remain unresolved; completing A4.1 does not pass or erase A4.0. This report is post-result and does not authorize A4.2/A4.3.

## Preregistered gates and outcomes

| Gate | Threshold/rule | Observed | Outcome |
|---|---|---|---|
| A4.1 completeness | 45 planned variants, each once | 45 attempted; 45 exit-0 successes | Complete |
| Launch guard | ≥8 GiB MemAvailable; zero swap | Per-run guards recorded; all passed | Pass |
| Convergence censoring | >180 s or NaN is censored | Censored contributors in OLSR N=92/162 and DSDV at all N | Applied |
| Warm-up | ceil(1.5 × five-family maximum), only if no censor | See table below | Derived/not derivable |
| DSDV outage exclusion | Any longest post-first-delivery gap >5.0 s excludes that graph/protocol cell later | RGG N=162 DSDV: 5.32650648 s | Exclude that cell |
| Phase 6D comparison | Report whether any DSDV gap reaches 15 s | None; DSDV maximum is 5.32650648 s | No comparable 15-s DSDV outage |

## Convergence and warm-up

The selected A4.0d readiness candidate was applied provisionally for A4.1 only: unique schedule-matched probe receptions, $G=1$ s, trailing 10-s window, minimum 10-s observation age, and beginning of the final contiguous passing suffix. C95 remains unadopted. The per-size summary uses five family-r1 graphs; values and descriptive Pearson correlations are in [derived_4.1.csv](derived_4.1.csv) and [convergence_correlations.csv](convergence_correlations.csv).

| Protocol | N=42 min / median / max (s); warm-up | N=92 min / median / max (s); warm-up | N=162 min / median / max (s); warm-up |
|---|---|---|---|
| OLSR | 19.434 / 19.762 / 20.745; 32 frames | 20.254 / 35.982 / 180.497; not derivable | 19.434 / 70.753 / 233.410; not derivable |
| AODV | 10.259 / 113.642 / 113.970; 171 frames | 10.259 / 13.210 / 115.283; 173 frames | 10.259 / 12.065 / 12.231; 19 frames |
| DSDV | 10.260 / 160.337 / 205.393; not derivable | 115.282 / 205.396 / 235.376; not derivable | NaN / 178.730 / NaN; not derivable |

Every DSDV size has at least one censored family run. Do not substitute another convergence value or impute a warm-up. These outcomes follow the frozen rules; they do not themselves authorize load runs.

## Delivery-gap correction and readiness review

The original `gap_from_packets()` wrongly treated the global Tx callback sequence as a per-flow packet index. In particular, it wrote NaN for OLSR despite hundreds of delivered probe packets. Offline correction identifies the single probe flow using its frozen app-Tx schedule (0.1 s start, 0.16384 s interval), joins Rx to a unique Tx by `app_tx_time_s`, and ignores the non-identifying global sequence. All 45 logs passed schedule validation: 1,459 scheduled Tx each; no duplicate Tx, unmatched Rx, malformed/off-schedule rows, or duplicate Rx rows. The per-run before/after audit, including the largest-gap endpoints, is [all_up_gap_recompute.csv](all_up_gap_recompute.csv); reproducible offline code is [recompute_4_1_delivery_gaps.py](recompute_4_1_delivery_gaps.py). Corrected gaps are written to the A4.1 rows in [runs.csv](runs.csv), [derived_4.1_runs.csv](derived_4.1_runs.csv), and [derived_4.1.csv](derived_4.1.csv). No simulator was rerun.

| Protocol | N=42 max gap (s) | N=92 max gap (s) | N=162 max gap (s) |
|---|---:|---:|---:|
| OLSR | 0.338486 | 1.306436 | 23.578562 |
| AODV | 0.179210 | 0.200806 | 0.190767 |
| DSDV | 1.271390 | 1.995780 | 5.326506 |

Two material long intervals were observed: BA/OLSR N=162, 121.198457–144.777019 s (23.578562 s, above 15 s); and RGG/DSDV N=162, 179.999402–185.325909 s (5.326506 s). Only the latter triggers the preregistered DSDV exclusion, and it is below 15 s. Thus the corrected gap observations now span all three sizes and reveal strong protocol/size heterogeneity. The provisional $G=1$ detector did recover after the long BA/OLSR gap, but this single-run evidence does not establish a generally appropriate later-stage detector. Reassess the detector and censoring behavior before considering any later-stage proposal; do not silently change A4.1's registered analysis.

Pearson convergence-vs-N correlations across all 15 family-size observations are descriptive: OLSR 0.368, AODV −0.522, DSDV 0.257. Diameter correlations by protocol and size are preserved in the linked correlation table; no causal or ranking interpretation is made.

## Runtime and accounting

Per-protocol × N process-wall min / median / max across the five families (seconds):

| Protocol | N=42 | N=92 | N=162 |
|---|---:|---:|---:|
| OLSR | 14.896 / 17.502 / 32.989 | 53.477 / 64.044 / 79.989 | 260.690 / 301.675 / 341.511 |
| AODV | 11.650 / 12.543 / 15.003 | 32.878 / 37.888 / 43.648 | 169.348 / 178.378 / 186.378 |
| DSDV | 20.559 / 22.463 / 24.920 | 99.110 / 105.635 / 130.433 | 418.308 / 517.210 / 580.463 |

Raw per-run values and provenance remain in [runs.csv](runs.csv) and the 45 run directories. Alpha accounting after completion: 58 A4 attempts; 70/300 total Alpha variants. A4.2, A4.2 φ=2%, and A4.3 remain at zero attempts. See [budget.md](../budget.md) and [Alpha limitations](../LIMITATIONS.md).

Integrity checks: the refreshed A4.0d manifest verifies 64/64 entries; the protected A4.0c output manifest verifies 31/31. Its frozen input manifest verifies 116/119; the three differences are the intentionally updated A4 runner and live A4 ledger plus the separately approved fixed ns-3 source (the pre-patch source identity remains preserved). No A4.0c artifact or hash manifest was edited. Preregistration and amendments 1–2 retain their registered hashes.

## Disposition

A4.1 is complete under its registered attempt, censoring, warm-up, and DSDV gap rules. The RGG N=162 DSDV cell is excluded from later load/replication metrics under preregistration; this is not a five-family DSDV protocol-drop verdict. No N=162 protocol-drop verdict is asserted. Readiness remains provisional and requires reconsideration given the newly observed multi-size gap heterogeneity. Stop here: no later stage, retry, or additional simulator variant is authorized.
