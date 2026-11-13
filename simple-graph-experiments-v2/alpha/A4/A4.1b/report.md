# A4.1b — offline detector, gaps, and warm-up reconciliation

**Written after A4.1b results.** Offline only: 0 variants; no ns-3 invocation, simulator, or rerun. A4.0*/A4.1 artifacts, preregistration, and amendments were read-only. The only external edit is this stage's single entry in [Alpha gates](../../gates.md). Budget remains 70/300; A4.2/A4.3 are unauthorized.

Frozen preregistration SHA-256: `6d26c7359008e64ab1975a644f7e59d6fa320143396c5f53b0f3c7998c992a35`. Analysis implementation: [analyze.py](analyze.py); runner [run.sh](run.sh). A4 runner source: [a4.py](../a4.py), SHA-256 `e842079d3365d8b1cfc39dcb725420bfa4d47908ea43211c5c6aaecd73ea6499`.

## G1–G3 outcomes

- **G1 PASS:** 0/45 mismatches at ≤0.5 s. NaN matches NaN only. Every recomputed packet-log readiness matches `derived_4.1_runs.csv`.
- **G2 PASS:** 25 applicable runs (corrected max gap ≤1 s); 0 violations of readiness ≤ first delivery +10 s.
- **G3 PARTIAL / overall FAIL:** 4/9 protocol×N warm-ups valid; 5/9 are `not_derivable_censored` (OLSR N=92/162; DSDV N=42/92/162). No `invalid_pending_detector` cell.
- On any hypothetical mismatch, the frozen cause categories are stale input / extra undeclared condition / implementation bug. No mismatch occurred, so none is assigned.

## Step 1 — source and AODV cluster

The producing path is `run_4_1()` → `run_variant()` → `summarize_run()` → `readiness_from_probe_packets()` in [a4.py](../a4.py#L219-L301). It reads the packet log's schedule-matched Tx/Rx app timestamps (with nonnegative sequence as a validity filter); convergence does **not** read `all_up_gap_s`, the old sequence-derived gap, corrected gap CSVs, PDR, or a loss counter. Thus the gap correction is not a stale convergence input. The helper applies unique Rx spacing over trailing 10-s windows, G=1 s, minimum age 10 s, and returns the first event in the final passing suffix; it does not calculate a packet-count PDR window.

Four AODV runs are in 113–115 s: three N=42 (RGG/WS/ER) and one N=92 (RGG). Their first deliveries are 104.484–105.462 s; readiness follows by 9.000–9.159 s. This is not one shared readiness timestamp. It is consistent with the written 10-s minimum observation age plus the suffix rule; no extra PDR/loss condition is present in the source. The registered warm-up is 171/173 frames because this valid late readiness is the maximum in those cells, not because max delivery gaps are large.

### Per-run first delivery and convergence

| Family | N | Protocol | First delivery (s) | Registered convergence (s) | Recomputed readiness (s) | Max gap (s) |
|---|---:|---|---:|---:|---:|---:|
| geodesic | 42 | olsr | 11.5224314 | 20.5816611 | 20.5816611 | 0.17381 |
| geodesic | 42 | aodv | 1.76906107 | 10.9151012 | 10.9151012 | 0.168795957 |
| geodesic | 42 | dsdv | 1.20133918 | 10.2600251 | 10.2600251 | 0.310290303 |
| rgg | 42 | olsr | 10.6596623 | 19.7621768 | 19.7621768 | 0.17405 |
| rgg | 42 | aodv | 104.811741 | 113.970177 | 113.970177 | 0.168344 |
| rgg | 42 | dsdv | 21.3553309 | 160.337181 | 160.337181 | 1.26064282 |
| ws | 42 | olsr | 10.6867563 | 19.7624609 | 19.7624609 | 0.17154 |
| ws | 42 | aodv | 104.811205 | 113.970461 | 113.970461 | 0.16729 |
| ws | 42 | dsdv | 0.209977926 | 145.263901 | 145.263901 | 1.27139032 |
| er | 42 | olsr | 10.310445 | 19.434213 | 19.434213 | 0.338486 |
| er | 42 | aodv | 104.483757 | 113.642213 | 113.642213 | 0.172541012 |
| er | 42 | dsdv | 0.227787257 | 190.319617 | 190.319617 | 1.21466022 |
| ba | 42 | olsr | 11.6445147 | 20.7449329 | 20.7449329 | 0.21500327 |
| ba | 42 | aodv | 0.388565927 | 10.259173 | 10.259173 | 0.17921 |
| ba | 42 | dsdv | 1.15695732 | 205.392613 | 205.392613 | 1.22450427 |
| geodesic | 92 | olsr | 11.0707658 | 180.497333 | 180.497333 | 1.30643647 |
| geodesic | 92 | aodv | 4.05167688 | 13.2097128 | 13.2097128 | 0.168344292 |
| geodesic | 92 | dsdv | 9.61040497 | 219.648397 | 219.648397 | 1.2813588 |
| rgg | 92 | olsr | 11.1812695 | 20.2542649 | 20.2542649 | 0.200458546 |
| rgg | 92 | aodv | 105.462102 | 114.462266 | 114.462266 | 0.17030057 |
| rgg | 92 | dsdv | 15.9972866 | 115.28175 | 115.28175 | 1.28824348 |
| ws | 92 | olsr | 12.2594809 | 21.4028488 | 21.4028488 | 0.179222142 |
| ws | 92 | aodv | 106.120712 | 115.283168 | 115.283168 | 0.167580068 |
| ws | 92 | dsdv | 5.66521606 | 205.396305 | 205.396305 | 1.21556623 |
| er | 92 | olsr | 10.3441274 | 155.913217 | 155.913217 | 1.17301967 |
| er | 92 | aodv | 2.76307309 | 11.8978571 | 11.8978571 | 0.173834616 |
| er | 92 | dsdv | 16.1455862 | 235.375617 | 235.375617 | 1.53109326 |
| ba | 92 | olsr | 10.3232548 | 35.9824851 | 35.9824851 | 1.18739667 |
| ba | 92 | aodv | 0.390662357 | 10.2591729 | 10.2591729 | 0.200806211 |
| ba | 92 | dsdv | 46.2868095 | 135.525269 | 135.525269 | 1.99577982 |
| geodesic | 162 | olsr | 13.254763 | 70.7529644 | 70.7529644 | 1.17293617 |
| geodesic | 162 | aodv | 3.06359687 | 12.0651251 | 12.0651251 | 0.16948814 |
| geodesic | 162 | dsdv | 0.4319423 | 133.305285 | 133.305285 | 1.27678178 |
| rgg | 162 | olsr | 11.0954117 | 20.2551177 | 20.2551177 | 0.358696 |
| rgg | 162 | aodv | 3.08465468 | 12.2269579 | 12.2269579 | 0.19076747 |
| rgg | 162 | dsdv | 1.35958752 | 235.377322 | 235.377322 | 5.32650648 |
| ws | 162 | olsr | 13.7958247 | 80.5509793 | 80.5509793 | 1.27669133 |
| ws | 162 | aodv | 3.10716049 | 12.2307646 | 12.2307646 | 0.17056 |
| ws | 162 | dsdv | 9.72030165 | 221.617439 | 221.617439 | 1.45863266 |
| er | 162 | olsr | 10.3674708 | 19.4344971 | 19.4344971 | 0.827680519 |
| er | 162 | aodv | 0.943523811 | 10.2594568 | 10.2594568 | 0.17975 |
| er | 162 | dsdv | 1.31021422 | nan | nan | 2.25577023 |
| ba | 162 | olsr | 11.3586227 | 233.409537 | 233.409537 | 23.5785621 |
| ba | 162 | aodv | 1.77401718 | 10.9148171 | 10.9148171 | 0.189668885 |
| ba | 162 | dsdv | 9.92302655 | 135.842726 | 135.842726 | 2.21423589 |

## Step 2 — DSDV timer alignment and gap distribution

All 15 DSDV runs contain at least one delivered-packet gap start within ±0.5 s of a positive 15-s multiple: 1,123 matching intervals total (N=42: 414; N=92: 357; N=162: 352). Matching gap-length ranges are N=42 0.001178–1.260643 s, N=92 0.000688–1.531093 s, and N=162 0.000614–5.326506 s; the median is 0.16384 s at each size. All starts/lengths are in [dsdv_15s_timer_gap_events.csv](dsdv_15s_timer_gap_events.csv). RGG/DSDV N=162 starts at 179.999402 s, 0.000598 s before 180 s, and lasts 5.326506 s. App Tx schedule points are spaced 0.16384 s; the ±0.5-s matching window is broad relative to that spacing, so alignment is descriptive, not timer-causality evidence.

Across all 45 run-level maximum gaps: min 0.167290 s, median 0.338486 s, p90 1.809905 s, max 23.578562 s; 2/45 exceed 5 s, 1/45 are ≥15 s. The strict preregistered >5-s threshold has one observed DSDV crossing (RGG N=162) but only 2/45 maximum-gap crossings overall; this sparse result does not validate the threshold as a predictor. Do not compare it as equivalent to the Phase 6D 15-s outage: warm-up and propagation setups differ.

## Step 3 — BA/OLSR N=162 event evidence limits

The A1 BA graph has max-degree hub node 0 (degree 37); the probe pair is 49→103 and one canonical A1 shortest path is 49→10→0→2→63→103. [Whole-run per-node counters](ba_olsr_node_overview.csv) retain control packets/bytes by message type, MAC/PHY/queue counters, and forwarding for these nodes. These counters have no event timestamps; equal-length 110–150-s versus other windows cannot be computed. The A4.1 command did not enable `emitControlUnparsed`; no `control_unparsed_*` field exists in this run's saved per-node, packet-diagnostics, or result CSVs, so no time-local parser counter is available.

Whole-run evidence (HELLO/TC/other packets; MAC retries; final failures; queue drops; PHY collision-class drops; forwarded packets):
| Node | Degree / role | HELLO p/b | TC p/b | Other p/b | retries/final | queue/TX drop | PHY collision | forwarded |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 0 | 37 / hub + path | 79/28060 | 220/177656 | 157/21028 | 267/8 | 0/0 | 9494 | 434 |
| 2 | 18 / path | 77/15272 | 227/175492 | 151/18024 | 202/7 | 0/0 | 3071 | 404 |
| 10 | 19 / path | 75/15044 | 236/177640 | 126/18080 | 412/26 | 0/0 | 2945 | 473 |
| 49 | 4 / path | 81/10340 | 218/168096 | 57/13784 | 568/30 | 0/0 | 324 | 0 |
| 63 | 8 / path | 76/10240 | 216/167096 | 89/15632 | 69/2 | 0/0 | 827 | 401 |
| 103 | 4 / path | 78/10424 | 219/164692 | 54/13144 | 13/0 | 0/0 | 296 | 0 |

Selected-node PHY raw reasons (all-run counts; full values, including TXING/RXING and abort reasons, are in the CSV): node 0 BUSY_DECODING_PREAMBLE=315, PREAMBLE_DETECT_FAILURE=5,941, RXING=4,208; node 2=112/1,315/1,872; node 10=106/1,217/1,793; node 49=16/86/244; node 63=25/293/615; node 103=13/54/261. OLSR MID/HNA control counts are zero on these selected nodes.

The full CSV also gives each selected node's PHY raw-reason breakdown. Across the entire run, retry maximum is node 49 (568), not hub 0 (267); queue drops are zero network-wide. Hub 0 has 9,494 collision-class drops, the maximum (network mean 575.46), but this is not time-local. Node 0 and path node 2 have similar whole-run control totals (456 vs 455 packets; TC 220 vs 227); path-node retry counts are heterogeneous. Hub-load association is possible but untested for the event window. TC/MPR timing cannot be aligned without timestamps. Telemetry/parser artifact cannot be confirmed or excluded locally because the unparsed counter was not emitted. **The saved evidence cannot discriminate causes; no cause is inferred.**

## Step 4 — correlations

Correlations are reported only for AODV, whose three size cells pass G1/G2/G3: convergence-vs-N Pearson r = −0.521556 (n=15); diameter r by N=42/92/162 = 0.484193/0.770287/0.892316 (n=5 each). No censored values were included. OLSR and DSDV correlations are not reported because one or more contributing warm-up cells fail G3. These are descriptive only.

## Step 5 — warm-up status and proposal-only options

| Protocol | N=42 | N=92 | N=162 |
|---|---|---|---|
| olsr | 32 (derived; all five runs pass G1/G2 and are uncensored) | not_derivable (not_derivable_censored; one or more runs censored (>180 s or NaN)) | not_derivable (not_derivable_censored; one or more runs censored (>180 s or NaN)) |
| aodv | 171 (derived; all five runs pass G1/G2 and are uncensored) | 173 (derived; all five runs pass G1/G2 and are uncensored) | 19 (derived; all five runs pass G1/G2 and are uncensored) |
| dsdv | not_derivable (not_derivable_censored; one or more runs censored (>180 s or NaN)) | not_derivable (not_derivable_censored; one or more runs censored (>180 s or NaN)) | not_derivable (not_derivable_censored; one or more runs censored (>180 s or NaN)) |

| 4.2 option (not selected) | Run/frame consequence | Variant consequence / assumption |
|---|---|---|
| Fixed protocol/size warm-up from noncensored data | Keep registered 120 measured frames; total = warm-up +120. AODV valid values give 291/293/139 frames at N=42/92/162. OLSR has only N=42=32; DSDV has no uncensored same-cell estimate. | 0 added variants if replacing existing cells (≤135); extrapolation to censored sizes assumes transfer not supported by evidence. |
| Fixed 180-frame warm-up | 300 total frame-seconds with 120 measured; exceeds a 240-frame total by 60. Still below observed censored convergence up to 235.376 s. | 0 added variants; does not guarantee readiness. |
| Per-run readiness-gated 120-frame measurement | Variable warm-up +120, potentially >240; must measure readiness under load and may need extra duration. | Same cell count if replacing runs; assumes detector transfers under load; runtime increase unknown. |
| Drop affected protocol×N cells | Avoids unsupported warm-up, reduces planned executed cells. | No added variants; DSDV censor skips up to 45/24 in 4.2/4.3; OLSR censor N92/162 skips up to 30/16. AODV N42/92 pass gates; a discretionary drop would free 30/16 but is unsupported by these gates. |

The RGG/DSDV N=162 outage exclusion is a subset of DSDV's censored set: 3 4.2 load-role variants and at most 2 4.3 replication variants, not additive. No option is chosen.

## Step 6 — budget and stop

Spent 70/300; registered maxima 4.2=135 and 4.3=72 leave 23 spare. Current preregistered warm-up exclusions touch up to 75 4.2 variants (45 DSDV +30 OLSR) and 40 4.3 variants (24 DSDV +16 OLSR); the DSDV N162 RGG 3/2 outage counts are included above. AODV N42/92 are valid despite the late first deliveries; no current exclusion is indicated. See [budget dependencies](budget_dependencies.csv).

### Decisions needed (no action taken)

1. Whether to retain the validated provisional G=1 readiness rule for any later-stage proposal, without changing A4.1 results.
2. How to handle the censored DSDV cells and censored OLSR N=92/162 cells: skip per preregistration or propose a separately registered warm-up/window design.
3. Whether the AODV N=42/92 late-first-delivery warm-ups are acceptable as recorded (G1–G3 pass), or whether a separately justified change should be proposed.
4. Whether to preserve the registered >5-s DSDV exclusion (including RGG N=162); no alternative is applied here.
5. No A4.2/A4.3 execution is authorized by this report; explicit direction is required before any later-stage work.

**STOP.** No reruns, detector change, cell disposition, A4.2, or A4.3 were performed. See [Alpha limitations](../../LIMITATIONS.md).
