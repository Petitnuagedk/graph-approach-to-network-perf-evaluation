# A2g-1 result — stored-trace provenance and edge flicker

**Gate: FAIL for H1; artifact integrity passed.** This was an offline analysis only: no traces were regenerated, and A2c/A2f-3 files were read-only.

## Provenance

All 300 A2c configs identify the frame sampler as the legacy iid frame-pool path (`behavior=patched` applies to its timeline generation, not the frame sampler). The stored A2c frame source hash is identical across configs and matches the source mechanism: each candidate frame independently draws every skeleton edge as Bernoulli(`p_edge`), classifies it by S–R connectivity and shortest path, and stores it in the up/down pool. The assembler samples a frame with replacement for each timeline state; up path IDs bind to groups, and down frames are sampled from the disconnected pool. Thus the stored assembled traces are not unconditioned independent Bernoulli frame samples even though their pool-generation edge draws are iid.

All 300 A2f-3 configs record `frame_behavior=patched-v3` and `timeline_behavior=uk`. The donor sampler creates independent per-edge two-state Markov chains with stationary occupancy pi=.5, then projects each frame to the fixed S–R target state before assembly. It is therefore not an iid-frame comparator. The shared-source, patched-source, finite-pool, and S–R conditioning mechanisms are central to interpreting toggles.

## Registered H1 test

H1's primary statistic excluded edges on the static lexicographically canonical shortest S–R path and computed toggles only within each 120-frame trace, over 119 adjacent transitions. All 300 configs, frame sequences, graph hashes, and edge files passed integrity checks; all rows had a nonempty non-constraint edge set and exactly 120 frames. The numeric threshold was $|q_{obs}-2p(1-p)|\le0.05$ on at least 90% of A2c rows.

| p_edge | iid expectation $2p(1-p)$ | Rows passing | Fraction |
|---:|---:|---:|---:|
| .3 | .42 | 25/100 | .25 |
| .5 | .50 | 25/100 | .25 |
| .7 | .42 | 34/100 | .34 |
| **All** | — | **84/300** | **.28** |

The registered required count was 270/300. Observed 84/300 (28%) fails H1. This does not contradict the underlying iid per-edge pool-generation draw. It shows that the saved, assembled, connectivity-conditioned finite-pool traces do not preserve the unconditioned iid toggle baseline on this edge set. Across A2c traces, non-constraint toggle mean ± sample SD (`ddof=1`) was .3354 ± .0833. Across the 300 A2f-3 projected Markov traces, it was .2594 ± .0694; this is descriptive only, not an H1 comparator.

The per-trace CSV preserves every registered family/life/seed/p row, toggle rate for all edges, excluded path edges and non-constraint edges, config and graph hashes, source hashes, and row-level H1 status. `summary.json` includes per-family×life×p means and sample SDs across the five seeds, all H1 counts, provenance counts, and source-hash sets. There were no corrupt or missing A2c rows, and no rows were silently excluded.

## Scope and limitations

The exclusion of all edges on the canonical static shortest path is deliberately conservative and common to both stored grids; A2c has no explicit edge-level connectivity projection. A2f-3's memory process is followed by S–R projection, so its toggle statistic includes projection effects. Only one N=92 realization per family appears in these stored grids; the probe pair was fixed by a structural rule. The timeline-diversity family is family-independent by construction. The generator is patched and non-upstream. This result is not a protocol-performance estimate; instantaneous per-frame S–R uptime remains the later-phase oracle, and waiting-permitted time-respecting reachability is descriptive only and must be called “allows store-carry-forward”. The MPC fail-closed change remains proposal-only; `alpha/EM/` is untouched.
