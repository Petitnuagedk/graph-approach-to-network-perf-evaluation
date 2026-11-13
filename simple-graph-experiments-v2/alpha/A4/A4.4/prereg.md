# A4.4 preregistration — static baseline

## Scope and decisions

A4.4 measures the static all-up baseline for five A1 graph families (`geodesic`, `rgg`, `ws`, `er`, `ba`), N={42,92,162}, and AODV/OLSR only: 30 variants. DSDV is excluded by user direction and this is not a routing verdict. One baseline phi is used per N: 0.05, 0.015, and 0.0065 respectively. These user-selected values are matched on the forwarded-load proxy only: flows × geodesic mean shortest path / N, approximately 3.0, 2.9, and 3.0 using geodesic lengths 2.92, 4.28, and 5.67. They are not matched on flows per node; the proxy uses geodesic lengths for every family and is therefore approximate.

## G0 units and pair count

The frozen A4 runner has `FRAME_RATE = 1.0`, so one frame equals one second. Its positive pair-count rule is `floor(x+0.5)` (the runner's positive branch of `llround`). Therefore the expected realized background flow counts are: N=42, `floor(.05*42*41/2+.5)=43`; N=92, `floor(.015*92*91/2+.5)=63`; N=162, `floor(.0065*162*161/2+.5)=85`. G0 passes.

## G-A budget

The recorded cap is 310. The recorded pre-A4.3 total was 160; amendment 1 added 40 new A4.3 attempts (10 reused rows do not consume variants), amendment 2 added 50, giving 250 new/attempted A4.3 variants and cumulative accounting 275/310 as recorded. A4.4 adds 30 variants (15 AODV and 15 OLSR), yielding 305/310. The hard cap is not exceeded. No budget file is edited.

## G-B configuration

Every run must write a configuration record and use `--interpolate=false`, `linkUpLossDb=10`, `linkDownLossDb=125`, `defaultLossDb=1000000`, `lossThresholdDb=150`, `txPowerDbm=20`, `fps=1`, `dataRate=50kbps`, `packetSize=1024`. A configuration mismatch blocks launch. No A4.3 run is reused: its total length differs from A4.4 and it is classified `superseded_by_A4.4`.

## G-C durations and window

Warm-up is 120/180/320 s for N=42/92/162. Sim time after warm-up is 300 s, so total run lengths are 420/480/620 s. The fixed measurement window is `[warmup, warmup+300]`. No timeout is installed; a user interruption is recorded. Each run logs start/end UTC, elapsed seconds, worker ID, configuration hash, and exit code. Two workers run under the A4.0d guard: at least 8 GiB `MemAvailable` and zero swap. No automatic retries.

## G-D, readiness, and outcomes

No A4.3 row is reusable; prior A4.3 rows are marked `superseded_by_A4.4`. Set `readiness_after_warmup` when the A4.1 readiness value for the family/N/protocol exceeds warm-up, and `readiness_undefined` when absent. The per-run pass criterion is probe PDR >= 0.99 and background median per-flow PDR >= 0.95 within the fixed window, but it does not stop execution. A flagged shortfall is `convergence-affected`; otherwise it is `indeterminate`. With one phi per cell, no congestion-candidate attribution is assigned. `control-amplified candidate` is descriptive only when control bytes per node rise while PDR falls; no routing or MAC cause is assigned without the per-type table. Extra analysis is labelled “written after A4.4 results”.

## Reporting and stop

The plan has one row per family/N/protocol. Per-run CSV fields include the baseline card parameters, PDR/delay fields, control packets/bytes by type with AODV RERR separate, forwarded-load Gini, MAC retry maximum, PHY collision-drop maximum, readiness flag, elapsed time, configuration hash, worker, and exit code. Report uses population summaries only and no ranking or ceiling language. After the 30 runs, report, manifest, and Beta design note, stop: no further phi, re-sweep, detector/window change, DSDV, or Beta execution.
