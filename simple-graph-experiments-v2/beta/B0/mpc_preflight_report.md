# MPC B0 preflight report

**Status:** pair materialization PASS; pool-aware exact MPC prototype PASS; registered B0 pending

## Pair materialization

The helper `flow_pair_manifest.cpp` implements the ns-3
`GenerateFractionFlowPairs` algorithm exactly: probe first, 43 rounded
background pairs for `N=42`, `phi=0.05`, `std::mt19937_64`, shuffled unordered
candidate pairs, and the same independent orientation draw. The generated
manifest contains 44 ordered pairs. `mpc_smoke.py` asserts equality between
that manifest and the `pairs` field passed to
`FrameGenerator.generateMPCFrames`.

## Dynamic construction gate

The first smoke test used an independent 44-pair timeline. It requested a
status vector absent from the finite MPC frame pool, so the builder correctly
stopped with `No pool for status ...`. No substituted frame or protocol result
was emitted.

A second prototype allocated timeline states from the finite pool with exact
multiplicity, while still using `force=False` and
`allow_hamming_fallback=False`. It selected 300 frames with exact status
matching, pair-specific path checks, and zero fallback. The output is
`mpc_smoke_geodesic_N42_r1.json`.

## Decision

Pair correspondence and exact pool-aware construction are proven for this
preflight. B0 is not yet a campaign PASS because the prototype does not yet
implement the registered life/stability acceptance design. B1/B2 and all B3
execution remain blocked until that acceptance run is recorded.