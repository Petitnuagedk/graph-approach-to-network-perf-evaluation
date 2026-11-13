# A2g-2 result — single-pair up/down pool supply

## Disposition

**H2 NOT SUPPORTED; execution completeness failed by one externally interrupted cell.** The registered grid has 810 unique cells. 809 produced successful pool metrics; the parent sweep process ended after logging 311 cells and before recording a result for the next cell. That prewritten cell was recorded as `failed_external_interruption` and was not retried. The other 498 never-started cells were then run once each, each with its own 60-second child limit. No timeout, substitution, seed replacement, or pool-cell rerun was performed. The failed cell is `er_N162_r1__p0.7__t10000__seed47`.

The preregistered H2 conditions independently fail on the observed data:

- Positive-down endpoint-isolation ratio: 532/732 = **72.68%**, below the required 80%. Ratio mean 2.3002, sample SD 2.0329 (`ddof=1`), maximum 16.6668.
- F=120 all-life p* non-increasing family sequences: 3/5 at 3,000 trials (fails the minimum 4/5); 4/5 at 10,000 trials (passes that component).
- Pooled descriptive slopes pass their registered sign check: mean endpoint degree −0.02351 and graph mean degree −0.07148 across 30 defined graph×trial rows. N slope −0.00009174 and diameter slope −0.00658 are descriptive only.
- Overall H2 is NOT SUPPORTED because completeness, endpoint-isolation proportion, and the 3,000-trial monotonic-family threshold do not pass. No gate or threshold was changed.

## Design and execution integrity

The frozen design was 15 A1 realization-1 graphs (five families × N={42,92,162}) × p_edge={.1,.2,…,.9} × pool trials={3000,10000} × seeds={11,29,47}. The saved ledger has 810 unique rows, 810 configs, 810 status records, and 809 metrics files. All 809 successful cells are recorded as success; one is recorded as externally interrupted. Config hashes were verified against the ledger. Each config carries the frozen preregistration hash, the pre-run runner hash, graph-edge hash, source hashes, graph probe and degree covariates, and 60-second timeout. Metrics preserve up/down pool counts, distinct shortest-path group counts, connectivity fraction, exact endpoint-isolation probabilities, and F=120/240 readiness.

The parent-process interruption did not reach its 60-second per-operation limit: it was an orchestration interruption between cells, and the in-flight cell's result/status was absent. In keeping with the no-retry rule, that cell remains missing and counts against the all-operations-successful criterion. The continuation added only cells that had no config or result artifacts at the time it began.

## Registered supply findings

The summary table records the seed mean and sample SD of pool counts by graph, p_edge, and trial size, plus distinct shortest-path groups, connectivity fraction, and strict quota readiness. F=120 all-life readiness means up/down counts at least 108/84; F=240 means at least 216/168. These are strict distinct-entry capacities and are deliberately separate from the existing replacement assembler's nonempty-pool feasibility.

All family/size sequences below are mean seed-level F=120 p* in increasing N order {42,92,162}; an em dash denotes no qualifying p* on the registered grid:

| Family | Trials | p* sequence | Non-increasing? |
|---|---:|---|---|
| BA | 3,000 | .6667, .6333, .6000 | yes |
| BA | 10,000 | .7667, .7333, .7000 | yes |
| ER | 3,000 | .5000, .7000, .5000 | no |
| ER | 10,000 | .6000, .8000, .6000 | no |
| Geodesic | 3,000 | .5000, .5000, .5000 | yes |
| Geodesic | 10,000 | .6000, .6000, .6000 | yes |
| RGG | 3,000 | .6000, .6000, .5667 | yes |
| RGG | 10,000 | .6000, .6000, .6000 | yes |
| WS | 3,000 | .5000, .5333, .6000 | no |
| WS | 10,000 | .6000, .6000, .6000 | yes |

All 30 graph×trial rows have all three seed p* values defined. F=240 p* means and sample SDs, as well as the full seed-level F=120/240 values, are retained in the linked CSV artifacts; no p* was clamped or extrapolated outside p_edge .1–.9.

## Aggregation correction record

After all pool operations had ended, the frozen `run_a2g2.py` summarizer raised `KeyError('endpoint_degree_S')`: `graph_records()` uses `degree_s`/`degree_r`, while the slope calculation requests uppercase aliases. Pool generation and operation records were already complete. The error was fixed only in a separate aggregation-only wrapper that supplies those aliases in memory and invokes the unchanged summary calculation. It did not modify the frozen runner, configs, pool results, thresholds, or operation statuses and launched no workers. The wrapper hash is recorded below. The H2 completeness failure and independent gate failures remain visible in the generated summary.

## Files

- Frozen preregistration: [A2g-2 preregistration](../a2g2_prereg.md).
- Frozen pool runner: [run_a2g2.py](../run_a2g2.py).
- Aggregation-only repair: [aggregate_a2g2.py](../aggregate_a2g2.py).
- [Operation ledger](operation_log.csv) and [all per-operation configs/results](operations/).
- [Per-operation index](per_operation.csv), [per-seed supply and demand readiness](per_seed_supply.csv), [pool means and sample SDs](pool_summary_by_graph_p_trials.csv), [per-seed p* values](pstar_per_seed.csv), [mean/sample-SD p* by graph and trial count](pstar_by_graph_trials.csv), [H2 summary](summary.json).

SHA-256 identities:

- preregistration `5e1ec283901728a9cf89f9a39dd6795c508793118e3a5c0329b6596a46247754`
- frozen runner `5359417fcb4737f907b8a04d3a6b0be10b9bf5b17d522ff48f33e66de9add5b1`
- aggregation-only wrapper `e28edd190cd19e49e48bb8cf78b5715f2b8256b4f4b83c5c2668ba298acbaa85`
- operation ledger and generated table hashes are recorded in the A2g final report after final artifact validation.

## Limits

One realization per family/size; graph and probe pairs are fixed by the A1 structural rule. The pool source is the unchanged legacy iid candidate-frame sampler, not the adopted `uk` + `patched-v3` timeline/frame combination. The strict quota-capacity rule is more demanding than with-replacement assembly and must not be conflated with its nonempty-pool criterion. The registered endpoint-isolation probability is only a lower bound on S–R disconnection, not a full disconnection model. These are offline generator-only results; no ns-3, protocol variants, or A3 were started.
