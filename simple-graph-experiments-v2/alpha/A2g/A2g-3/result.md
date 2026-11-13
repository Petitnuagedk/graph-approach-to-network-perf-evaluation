# A2g-3 result — patched edge memory driven by `uk`

## Disposition

**H3 PASS.** All 90/90 registered child operations completed successfully, no retries or substitutions; longest parent-measured operation was 0.8641 s, below the registered 60-second timeout. All 30/30 family×life×`(π,L)` cells qualified (three passing seeds per cell), exceeding the registered minimum of 27/30. `(π=.8,L=2)` remained mathematically infeasible (`p01=2`) and was not run.

All per-operation criteria passed 90/90: exact `uk` U/K, exact instantaneous S–R mask and U connected frames, all edges inside the A1 skeleton, projection fraction <=.05, projected edge-up fraction absolute error <=.05, and projected completed up-duration relative error <=.20. Worst observed margins were projection fraction 0.008032, projected |π̂−π| 0.012229, and projected relative duration error 0.108427. The unchanged A2d tolerances were used; none was relaxed.

## Parameter strata

Each row below pools five families × three seeds (n=15); report mean ± sample SD (`ddof=1`). The edge-duration estimator follows the A2d item-1 integrated diagnostic: pooled contiguous up-spells across skeleton-edge sequences over 120 frames. Raw and projected values are both shown because projection can shift the requested edge statistics.

| life | U/K | π | L | raw π̂ | projected π̂ | raw L̂ | projected L̂ | changed edge-time fraction |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| .5 | 60/5 | .5 | 2 | .50000 ± .00226 | .49888 ± .00256 | 1.98154 ± .00944 | 1.98181 ± .01046 | .003888 ± .000726 |
| .5 | 60/5 | .5 | 8 | .50117 ± .00550 | .49974 ± .00578 | 7.51610 ± .15262 | 7.36509 ± .17145 | .003599 ± .000742 |
| .5 | 60/5 | .8 | 8 | .79918 ± .00078 | .79322 ± .00160 | 7.50067 ± .07177 | 7.32855 ± .11828 | .006006 ± .001479 |
| .9 | 108/9 | .5 | 2 | .50000 ± .00226 | .50186 ± .00254 | 1.98154 ± .00944 | 1.99091 ± .01174 | .002767 ± .001315 |
| .9 | 108/9 | .5 | 8 | .50117 ± .00550 | .50278 ± .00585 | 7.51610 ± .15262 | 7.41912 ± .15744 | .002584 ± .001346 |
| .9 | 108/9 | .8 | 8 | .79918 ± .00078 | .79804 ± .00081 | 7.50067 ± .07177 | 7.44464 ± .06790 | .001189 ± .000300 |

The timeline mean-up is 12 frames in both lives by exact construction. This table does not imply that edge-chain duration L and Boolean timeline mean-up are the same variable; they are independently controlled axes. High-π projection shifted marginal estimates by at most 0.0068 across the strata, below the carried per-trace threshold. See [parameter summary](parameter_summary.csv), [30-cell summary](cell_summary.csv), and [all 90 per-seed results](per_seed_results.csv) for complete outputs.

## Execution and provenance

The frozen 90-cell grid used the five A1 N=92 fixed structural-rule pairs, lives .5/.9, F=120 and exact U/K `(60,5)/(108,9)`, feasible `(π,L)` values `(.5,2),(.5,8),(.8,8)`, and seeds `{11,29,47}`. Timelines were generated with the read-only A2f `uk` overlay and fed directly into the read-only A2d item-1 `patched-v3` frame sampler. Both raw Markov frames and projected frames were persisted. No finite-pool assembly was used in this stage. Per operation, the artifacts include config and hashes, schedule bits/path IDs, compressed per-edge/per-frame raw and projected states, changed-edge records, projected frames, metrics, and status. The full list and SHA-256 values are in [artifact manifest](artifact_manifest.csv).

- Preregistration: [a2g3_prereg.md](../a2g3_prereg.md), SHA-256 `39247091532fdf0107c4fbfc9ff4b1297aa4eae46a1b0254177920357c44ce98`.
- Runner: [run_a2g3.py](../run_a2g3.py), SHA-256 `9660a8c0685332b2f9bf4db892e4583463743c01f075e02079d146b08ba5a209`.
- Final aggregation-only helper: [aggregate_a2g3.py](../aggregate_a2g3.py), SHA-256 `6601471a5aff184999f5e96aad68ae4523bc29afc71a6d40b32bbb08caabd5c1`.
- Operation ledger: [operation_log.csv](operation_log.csv), SHA-256 `e1fc966ae07514fc701f3507f642ad3e7947dad4fef5c78cf46ef213b1d6bee0`.
- Per-seed table: [per_seed_results.csv](per_seed_results.csv), SHA-256 `0808340101ef51ae5baea894700fb0528ac13070cbb5ee3dd69128931fc941e8`.
- Cell table: [cell_summary.csv](cell_summary.csv), SHA-256 `db7aaa1b0d35698cfc553705870df0832e73ad4150cc5dc211b8d3950a354857`.
- Parameter table: [parameter_summary.csv](parameter_summary.csv), SHA-256 `cea66772d74bf801977601a7b6e38ec78e97d8840f0a5e62fe0ded4ae50c8eda`.
- Summary JSON: [summary.json](summary.json), SHA-256 `993c1ff92367c08be0affc916da132b46dcb5513a09cf9271cb201cb8e86fa33`.
- Artifact manifest: [artifact_manifest.csv](artifact_manifest.csv), SHA-256 `70b9615b892b9ed04c477e56d8da16d4922d31663fb1f1551c2e5d9396131a0b`.

The initial aggregation-only run failed on an optional CSV field-list argument after all 90 operation results existed. The report-only helper was corrected and aggregation completed; no worker was rerun and no data/config/threshold changed. The hash above is the final helper hash. Sampler and timeline source hashes are stored in all per-operation configs and validated by the worker before sampling.

## Limits and interpretation

One graph realization per family/size; patched non-upstream sampler; timeline diversity is family-independent by construction; probe pairs fixed by the A1 structural rule. Projection is not statistic-neutral: the raw/projected distinction is retained. No multipath claim beyond “single path, plus shared-source pairs as an exception”; MPC fail-closed remains proposal-only. Any future temporal reachability metric is descriptive and must say “allows store-carry-forward”; the operative oracle remains per-frame instantaneous usable S–R uptime with no waiting. No ns-3, protocol variants, or A3 were started.
