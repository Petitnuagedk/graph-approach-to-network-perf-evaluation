# Pilot cap accounting clarification

**Written 2026-10-08 before the target-length timing probe.** This clarification fixes the cap's counting unit; it does not set or imply a numeric pilot cap and it does not authorize a pilot campaign.

## Counting units

- The Phase 7 global hard ceiling is **300 protocol variants**. Charge each `graph-run` invocation by the number of routing variants it executes. One static-only invocation is 1 protocol variant; one invocation with OLSR/AODV/static is 3 variants. Offline generation/analysis costs 0 variants. Frame count, packet count, elapsed wall time, build time, and bare invocation count are not interchangeable with protocol-variant spend.
- The single static-only target-length timing probe costs **1 protocol variant**, whatever trace frame count or number of transmitted packets it uses. Its build/startup and simulator wall-clock measurements are recorded separately as time, not charged as variants.
- Any later pilot must state an explicit integer maximum in **protocol variants** before it starts. A wall-time estimate may inform that design but is not itself the cap. Each pilot cell/run cost is invocations × routing variants; the sum must not exceed the stated pilot cap or the 300-variant global ceiling. No pilot cap value is assigned by this clarification.
- The generator's separate feasibility cap $K=\min(\lceil U/5\rceil,D+1)$ is unrelated: $K$ counts positive S–R up-runs. It is not a simulation budget cap.

## Timing-probe gate

B2 has passed and the v2 generator redesign's offline acceptance audit passed (39 cells / 195 traces). The probe will use one validated 60-frame line trace (`path_life=0.5`, stability 0.8, persistency 0.75, realization 1), one static-only route, 50 kbps UDP, 1,024-byte packets, seed 42, 1 fps, 45-second first-frame warm-up, 125 dB down-loss, 10 dB up-loss, 150 dB threshold, and the opt-in v2 no-interpolation profile. Measure separately: (1) the elapsed time for an explicit ns-3 build/startup check, (2) graph-run overall elapsed time, and (3) the simulator-reported wall time in the result CSV. Preserve exact arguments, config, trace hash, source hash, and logs. This probe costs 1 protocol variant (projected total 15/300 if it runs).

A successful timing probe only supplies a measured cost for pilot planning; it does not authorize pilot runs. A separate pilot plan with its own integer protocol-variant cap requires review/approval before any campaign invocation.

## Post-probe clarification (2026-10-08)

The single timing run is an end-to-end smoke test, not a cost model: it used a 5-node trace, one S→R flow, static routing, 105 applied frames, and `--dumpRoutes=true`. The explicit build measurement was incremental. Its 0.227225 s simulator wall time and 1.385584 s wrapper-inclusive process time must not be projected to N=162, hundreds or thousands of flows, dynamic protocols, or larger route-table dumps. Their 1.158359 s difference is not an isolated startup measurement. The separately executed Alpha/Beta accounting decision now sets **Beta's cap unit to protocol variants** (invocations × routing variants), consistent with Alpha's unit. Beta's numeric cap remains unset and requires an approved Beta preregistration; no Beta run is authorized.
