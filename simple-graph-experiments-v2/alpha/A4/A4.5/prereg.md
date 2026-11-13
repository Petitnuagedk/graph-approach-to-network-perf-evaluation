# A4.5 preregistration — static all-links-up baseline

**Registration date:** 2026-11-12  
**Stage:** Alpha, documentation and execution authorization recorded by user decision.  
**Status:** registered before A4.5 execution.

## Purpose and scope

A4.5 provides the true static reference for the harness and operability results. Every frame contains the registered graph's complete undirected edge set; the same all-links-up frame is repeated for the full run. This replaces A4.4 as the static/Beta reference. A4.4 remains historical dynamic frame replay with unrecorded producer and parameters.

Scope is the five existing A1 graph families (`geodesic`, `rgg`, `ws`, `er`, `ba`), N=42, 92, and 162, with AODV and OLSR only: 30 protocol variants. DSDV is excluded by user direction. No Beta work is included.

## Frozen configuration

- phi: 0.05 at N=42, 0.015 at N=92, and 0.0065 at N=162.
- Integer flow counts use the existing positive-pair rule `floor(phi*N*(N-1)/2 + 0.5)`: 43, 63, and 85.
- Warm-up: 120, 180, and 320 s for N=42, 92, and 162.
- Post-warm-up simulation time: 300 s; measurement windows are [120,420], [180,480], and [320,620] s.
- One repeated all-up frame per timestep; frame count equals total run length at the registered 1 fps frame rate.
- Channel and traffic: interpolation OFF; 7B channel (`linkUpLossDb=10`, `linkDownLossDb=125`, `defaultLossDb=1000000`, `lossThresholdDb=150`); 802.11g; 20 dBm; 50 kbps; 1024-byte packets.
- Simulator seed policy: reuse the A4.4 seed identity, seed 42. Flow-seed derivation is retained from the frozen runner and is recorded in each configuration.
- Existing A1 graph realizations, graph IDs, probe pairs, and source identities are reused read-only.

## Gates

1. **G0 units:** plan has exactly 30 rows, all expected integer flow counts, and the frame count equals total run length.
2. **G1 static matrix:** every generated frame has exactly the A1 graph edge set and no non-skeleton edge; first, middle, and final frames hash identically.
3. **G2 configuration:** every run records args, seed, source hashes, ns-3 version, frame hash, and configuration hash; mismatches block launch.
4. **G3 execution:** each row is attempted once; failures and interruptions remain in the denominator; no automatic retries or substitutions. Require at least 8 GiB `MemAvailable` and zero swap at launch.
5. **G4 outcome:** report per-run probe PDR, background median/p10 PDR, delay, per-type control packets/bytes, forwarded-load Gini, MAC retries, PHY collision drops, readiness, elapsed time, and status. Pass criterion is probe PDR >= 0.99 and background median per-flow PDR >= 0.95 in the fixed window; it does not stop execution.

## Budget and accounting

A4.5 is classified as Alpha. The user's reconciliation decision selects the historical campaign claim of 335/340 as the authoritative pre-A4.5 Alpha accounting. The user then amended the Alpha cap to 365. A4.5 adds 30 protocol variants, giving a planned post-A4.5 accounting of 365/365. The budget gate therefore **PASSES** for the registered 30-row plan.

This amendment preserves the selected 335/340 ledger claim and does not silently replace the current `budget.md` 135/300 ledger. The discrepancy remains disclosed in the budget record.

## Stop boundary

The budget gate no longer blocks the registered A4.5 plan. A4.5 execution remains limited to the 30 registered variants, with no retries, substitutions, B0, or B1 implied by this document.
