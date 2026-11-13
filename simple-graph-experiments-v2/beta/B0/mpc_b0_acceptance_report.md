# MPC B0 acceptance result

**Date:** 2026-11-13  
**Result:** FAIL — target gate not met after doubled search horizon

## Search-horizon retry — 2026-11-13

The MPC pool horizon was doubled from 10,000 to 20,000 trials. The two-run
retry remained reproducible and continued to pass exact pair/status/path
matching with zero fallback, but it did not satisfy the registered life and
stability targets. Representative realized life remained approximately
0.90–0.95 and the up-run counts remained different from the required 31.

This shows that increasing pool size alone does not make the current
pool-aware status allocator target life/stability. The allocator still needs
an explicit constrained selection/search objective; no protocol stage is
authorized from this retry.

## User-modified horizon retry — 2026-11-13

The user increased the MPC search horizon to 100,000 trials and B0 was rerun
with the same two repetitions and all other parameters unchanged. The result
remained **FAIL**. Reproducibility, exact pair/status/path matching, and zero
fallback still passed. The life/stability target still failed: realized life
remained approximately 0.89–0.95 and the observed up-run counts remained
different from the required 31. The current output is in
`mpc_b0_acceptance.json`.

## User-confirmed configuration

- Scope: `geodesic_N42_r1`
- `N=42`, `phi=0.05`
- `p_edge=0.5`
- MPC trials: 10,000
- Pool seed: 11
- Timeline seed: 42
- Repetitions: 2
- Exact pool-aware status selection
- No Hamming or arbitrary-frame fallback

## Passed checks

- The exact 44-pair ns-3 manifest was used.
- Both repetitions used identical pair-manifest, timeline, and selected-frame hashes.
- Exact status matching passed.
- Pair-specific path selection passed.
- Fallback count was zero.
- Reproducibility passed.

## Failed check

The registered target was `life=0.5`, `stability=0.8`, with F=300. The rounded acceptance target is 150 up frames and 31 up-runs per pair. The pool-aware prototype selected available statuses from the percolation pool, but the resulting per-pair life values were approximately 0.90–0.96 rather than 0.50, and the up-run counts did not equal 31.

Therefore this run is not a B0 PASS. The result is recorded in `mpc_b0_acceptance.json`; no B1/B2/B3 run is authorized.

## Required next change

Implement a constrained pool-aware timeline allocator that selects 300 feasible MPC statuses while satisfying the per-pair 150-frame life and 31-up-run targets, or formally amend the target design. Do not relax exact matching or introduce fallback substitution.
