# A2g-5 result — fixed-duration operating-region synthesis

## Disposition

**Offline proposal only; no single globally validated operating region is established.** At a fixed 120-second experiment duration, both registered frame grids—1 fps (`F=120`) and 2 fps (`F=240`)—pass the preregistered frame-resolution screen against two 1024-byte packet intervals at 50 kbps (`0.32768 s`). All eight life×frame-grid combinations admit the exact 12-second target mean-up duration under `uk`. The packet-scale interval itself is below the smallest exact mean-up duration on every registered grid and is unreachable as an exact-quota mean-up target; no interpolation or rounding was applied.

A conservative **candidate for offline follow-up only** is `p_edge∈{.4,.5}` on the already tested legacy candidate pools, at either 3,000 or 10,000 trials. Each such observed point has strict all-life distinct-entry supply in all 45 planned graph×seed cells for both F=120 and F=240 (180/180 aggregate passes across the four frame-grid×trial-size combinations). This is not a transferable supply guarantee for the adopted `uk` + patched-v3 assembled-frame path: A2g-2 used the legacy iid pool sampler, H2 was not supported, and A2g-1's flicker gate failed. Actual use would require a per-configuration pool/readiness preflight and exact typed U/K feasibility checks. Points outside an individual graph×trial row's observed p* are **not established as strict-supply-ready**, not physically impossible.

## Fixed duration and exact-quota checks

The packet transmission interval is $1024×8/50000=0.16384$ seconds; the preregistered screen is twice this value, `0.32768 s`. All rows below share 120 seconds total duration. `K` is the integer number of up-runs for a target mean-up duration of 12 seconds; exact support is `U/K` and feasibility requires `1≤K≤Kmax=min(U,D+1)`. `Kmax` and exact minimum/maximum mean-up durations come from the A2f finite support. The packet target is tested directly against `{U/K}` and is not feasible in any row.

| fps | F | frame duration | life | U/D | Kmax | 12s target K | exact 12s target | exact mean-up range (s) | 0.32768s target | resolution screen |
|---:|---:|---:|---:|---:|---:|---:|---|---:|---|---|
| 1 | 120 | 1.0s | .3 | 36/84 | 36 | 3 | feasible | 1–36 | unreachable | pass |
| 1 | 120 | 1.0s | .5 | 60/60 | 60 | 5 | feasible | 1–60 | unreachable | pass |
| 1 | 120 | 1.0s | .7 | 84/36 | 37 | 7 | feasible | 2.2703–84 | unreachable | pass |
| 1 | 120 | 1.0s | .9 | 108/12 | 13 | 9 | feasible | 8.3077–108 | unreachable | pass |
| 2 | 240 | 0.5s | .3 | 72/168 | 72 | 3 | feasible | .5–36 | unreachable | pass |
| 2 | 240 | 0.5s | .5 | 120/120 | 120 | 5 | feasible | .5–60 | unreachable | pass |
| 2 | 240 | 0.5s | .7 | 168/72 | 73 | 7 | feasible | 1.1507–84 | unreachable | pass |
| 2 | 240 | 0.5s | .9 | 216/24 | 25 | 9 | feasible | 4.32–108 | unreachable | pass |

The fixed-duration table and machine-readable exact quota/support columns are in [fixed_duration_table.csv](fixed_duration_table.csv). In particular, 0.32768 seconds corresponds to 0.32768 frames at 1 fps and 0.65536 frames at 2 fps, not an exact `U/K` point; minimum feasible mean-up durations are 1.0/0.5 seconds for lives .3/.5, 2.2703/1.1507 seconds at life .7, and 8.3077/4.32 seconds at life .9. `uk` allows an exact supported quota to be requested, not a duration between support points.

## A2g-2 strict finite-pool supply evidence

Readiness counts below use the strict all-life distinct-entry demand: F=120 requires at least 108 up and 84 down entries; F=240 requires 216 up and 168 down. Counts are out of 45 planned graph×seed cells per p×trial×F. The sole missing operation is the registered external interruption at ER N=162, p=.7, 10,000 trials, seed 47; it is not retried or imputed and is counted as not established in the planned denominator.

| trials | p_edge | F=120 passes | F=240 passes |
|---:|---:|---:|---:|
| 3,000 | .3 | 36/45 | 36/45 |
| 3,000 | .4 | 45/45 | 45/45 |
| 3,000 | .5 | 45/45 | 45/45 |
| 3,000 | .6 | 24/45 | 10/45 |
| 3,000 | .7 | 6/45 | 0/45 |
| 10,000 | .3 | 42/45 | 39/45 |
| 10,000 | .4 | 45/45 | 45/45 |
| 10,000 | .5 | 45/45 | 45/45 |
| 10,000 | .6 | 45/45 | 42/45 |
| 10,000 | .7 | 12/45 | 11/45 |
| 10,000 | .8 | 6/45 | 0/45 |

The empirical all-seed `p_edge` window common to both F values and both candidate-trial counts is `.4–.5` on the registered 0.1 grid. At 10,000 trials, F=120 additionally has 45/45 passes at .6, while F=240 has 42/45; at 3,000 trials .6 readiness falls to 24/45 and 10/45. Thus no common all-grid claim is made for .6. The candidate window describes only the observed cells and finite tested graph realizations.

Across the 15 graphs, the observed per-seed p* ranges were: F=120, .5–.7 at 3,000 trials and .6–.8 at 10,000; F=240, .5–.6 at 3,000 and .5–.7 at 10,000. Full 60-row family×N×trial×F means, sample SDs (`ddof=1`), and individual seed p* values are in [pool_support_by_graph.csv](pool_support_by_graph.csv). Every p* outside a row's boundary is not established by the registered pool data. The complete 36-row p×trial×F readiness table, including zeros, all-grid denominators, and interruption accounting, is [pool_readiness_by_p.csv](pool_readiness_by_p.csv).

## Recommendation and limits

For offline design planning at 120 seconds, either 1 fps/F=120 or 2 fps/F=240 meets the registered temporal-resolution yardstick and supports 12-second mean-up targets at all four lives exactly. Prefer the conservative observed `p_edge=.4–.5` legacy-pool candidate range only as a **preflight region**, not as a validated setting for the adopted sampler. At each selected graph/configuration, enforce exact U/K support and typed rejection on infeasible requests, then verify actual pool quotas if using a pool-based assembly route. No interpolation, imputation, or p* extrapolation is licensed.

The evidence does not validate end-to-end delivery or routing. A2g-1 H1 failed (84/300 traces within toggle tolerance); A2g-2 H2 was not supported (including 532/732 positive-down cells meeting the endpoint-isolation ratio and a 3,000-trial monotonicity miss) and had one external interruption; A2g-3 H3 passed for the tested projected Markov/`uk` cells; A2g-4 found material up/down-conditioned background availability in all 40 fine strata. A2g-2's pool sampler is legacy iid and is not the A2g-3 adopted `uk`+patched-v3 frame path. The A2g-4 contrast is descriptive, not causal. There is one graph realization per family/size and fixed structural-rule probe pairs. `uk` is adopted. Multipath remains “single path, plus shared-source pairs as an exception”; MPC fail-closed remains proposal-only. The oracle is instantaneous per-frame usable S–R uptime with no waiting; time-respecting reachability is descriptive only and must say “allows store-carry-forward”.

This stage is a generator-only offline proposal: zero protocol variants, no ns-3, and no A3. **Stop at the end of A2g; do not start A3.**

## Reproduction and hashes

Command: `/home/hledirach/Documents/J2/.venv/bin/python /home/hledirach/Documents/J2/simple-graph-experiments-v2/alpha/A2g/analyze_a2g5.py` (Python 3.14.4).

- Preregistration [a2g5_prereg.md](../a2g5_prereg.md): SHA-256 `d3f4b27a5c70f8b4c888d412ae0ce71b8b3d981848fe0b5e42808348a9a6b9c0`.
- Analyzer [analyze_a2g5.py](../analyze_a2g5.py): SHA-256 `7fb6416cd0b5cac9e8d684ae06152f41bde3baff94bdd66d5a5871261ff47a02`.
- [Fixed-duration table](fixed_duration_table.csv): `df5002121868d2f5f8c91e343cb99093bbe74af3a9f722d4b6bd8e73f597cb27`.
- [Pool support by graph](pool_support_by_graph.csv): `8a43b9ffe55ee3d572af1380287f60053d36a33a835255bb28e78bee56d0f8ca`.
- [Pool readiness by p](pool_readiness_by_p.csv): `b08ba704d00c8f4c07153ac46c43481cad465b40918a95d2596685e005ea8f3c`.
- [Input manifest](input_manifest.csv): `661f168cf16885a07e2d119a76439fe23d391aa1e268dd22a0958c188d511874`.
- [Summary JSON](summary.json): `c0b9d91080e6dc33379ec3dea4f1bef39e2bbc39bba4de3a8a92523564d3dbbf`.
- [Artifact manifest](artifact_manifest.csv): `632c31e118142729b9068c190fa627d7e5b7864066c62a86ce0da250a9523e6d`.
