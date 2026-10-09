# Phase 7D target-length timing probe preregistration

**Written 2026-10-08 before the timing-probe graph-run invocation.** This is a single cost-measurement probe, not a campaign run or pilot sample. It follows the successful B2 regression and 7D offline validation; the original B1 aggregate-PDR gate remains failed, while the separate B1′ criterion and B2 passed. The user explicitly requested the timing probe after clarifying the cap accounting unit.

## Cap unit fixed before timing

Per [pilot_cap_accounting.md](pilot_cap_accounting.md), Phase 7's 300 ceiling and any later pilot cap are measured in **protocol variants**: graph-run invocations × routing variants. The probe runs one static-only routing variant, so it consumes exactly **1** variant independent of trace frames, packets, build seconds, or elapsed replay time. The cumulative total will be 15/300 if it completes (14 previously spent + 1). Build/startup and simulation times are measured in seconds and do not change the variant count. A future pilot's numeric maximum must be frozen as an integer protocol-variant count in its own approved plan; this document assigns no pilot cap and authorizes no pilot.

## Frozen target and run configuration

- Trace: v2 validated generator output at `7D/traces/line/pathlife_0.50__stability_0.80__persistency_0.75/realization_01/frames.csv` (60 frames, 1 fps, measured S–R uptime 0.5; SHA-256 `c722ea43c1052ffbe8c40a80a401886461e1b70cb2247ef8793bad6f38ce8bae`).
- Simulator: ns-3 at `/home/hledirach/Documents/sp1-sp2`; one `graph-run` invocation, routing static only, S→R.
- Traffic/channel: 50 kbps UDP, 1,024-byte packets, seed 42, loss threshold 150 dB, `channelProfile=v2` (resolved interpolation false), default loss 1,000,000 dB, Tx power 20 dBm, link-up loss 10 dB, link-down loss 125 dB, fps 1, warm-up 45 s in `first` mode, route dump enabled, usable-oracle diagnostics enabled.
- New output directory: `7D/timing_probe/run/`.
- Exact argument string is recorded in [timing_probe_invocation.json](timing_probe_invocation.json).

## Frozen measurements

1. Time a plain `./ns3 build scratch/graph-run` once before graph-run and record its elapsed seconds separately as build/startup/check time. Do not clean/rebuild or run extra graph-run invocations.
2. Time the single `./ns3 run "graph-run ..."` wall-clock duration with a monotonic shell timer; record that total separately.
3. Record ns-3's `wall_time_s` and `cpu_time_s` from the single static result row as simulator-reported replay timing.
4. Preserve console output, resolved config, trace hash, ns-3 source hash, exact arguments, result row, and output-file hashes. Report all measured durations literally; do not use them to change the already-consumed variant count.

This probe provides an observed cost at the stated 60-frame target only. It does not project unmeasured scales, authorize 7C, or approve a pilot. Before any pilot execution, prepare a separate design with its integer protocol-variant cap and obtain explicit approval.
