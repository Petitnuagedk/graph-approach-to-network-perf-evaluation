# Phase 6D(b) preregistration — focused DSDV all-up ladder investigation

Written before the new DSDV runs. The historical Phase 1–5 trees are read-only.

## Design

- Warm-ups: 0, 30, 45, 60, 90 s.
- Five graph-run replay runs use the archived all-up Phase 1 ladder, DSDV only, packet diagnostics and periodic route dumps, 50 kbps UDP, 1024-byte packets, 802.11g ad hoc, 20 dBm, 1 fps, and `warmupMode=first`.
- Five plain ns-3 runs use a fixed eight-node ladder embedding with a 1.2 m range channel, DSDV, 802.11g ad hoc, 20 dBm, the same UDP rate/size, and the same warm-up/traffic start timing. There is no trace matrix or replay scheduler in this control. Traffic runs from warm-up + 0.1 s to warm-up + 59 s, matching the replay trace's last frame timestamp.
- For each run record offered/received counts, PDR, route availability/route-table changes, and timing relative to DSDV defaults. DSDV default attributes from ns-3.46.1 source are PeriodicUpdateInterval=15 s, SettlingTime=5 s, Holdtimes=3 (45 s hold-down multiplier), EnableWST=true. Determine whether the alleged t=15–29 outage reproduces in each mode, and whether it is a no-route interval, route invalidation, or radio delivery failure.
- This experiment is diagnostic only. DSDV stays excluded from ranking unless evidence establishes a corrected/configured implementation.

## Exact run count and runtime estimate

Ten ns-3 invocations total: five replay + five plain. The archived same-topology DSDV replay at 60 s warm-up measured 3.02 s wall time. Estimate: 10 × 3.02 = 30.2 s, excluding command startup and compilation. The plain control duration matches the replay trace length plus warm-up.

## Stop condition

Do not extend the investigation or alter DSDV timers within this batch. If results remain inconsistent or the plain control is not topology-equivalent, report the specific limitation and keep DSDV excluded.

## Execution addendum

The 10 runs completed. Replay PDRs at warm-ups 0/30/45/60/90 s were 0.758/1.000/1.000/0.747/1.000; plain-control PDRs were 1.000 at every warm-up. Measured simulator times summed to 8.34 s (5 replay: 5.16 s; 5 plain: 3.18 s), excluding ns-3 command startup. The 60 s replay reproduced the 15.115 s receive gap (75.011–90.126 s), while its source route to R remained present in every sampled table from t=60 through t=118. It changed from sequence 10 at t=75 to sequence 12 at t=76 and retained a four-hop route via node 1; there were 0 app IP no-route, route-error, MAC queue, or MAC Tx drops, and 337 PHY Rx drop callbacks total. The plain 60 s control had no receive outage and PDR 1.000.

The no-replay control is topology-equivalent but not propagation-model-identical: it uses a 1.2 m range cutoff with 0 dB in-range loss, while graph-run uses 10 dB in-range loss plus the trace-matrix model and applies the frame scheduler every second. Therefore the results identify a replay/model-specific delivery failure, not a DSDV route-absence/invalid-route event; they do not isolate which radio-model or scheduler difference causes it. The 15 s timing coincidence with PeriodicUpdateInterval and the route sequence change are correlations, not proof of timer causality. DSDV remains excluded from ranking pending a separately authorized, narrower causal test.
