# Alpha A2g — offline Beta operating-region proposal

## Executive disposition

**A2g is complete. Stop here; do not start A3.** This phase was generator-only/offline: zero protocol variants, no ns-3, no protocol-performance testing, and no edits to `alpha/EM/`. The five preregistered outcomes are:

| Stage | Disposition | Main result |
|---|---|---|
| A2g-1 sampler provenance/flicker | **H1 FAIL; integrity PASS** | 84/300 stored A2c traces met the registered toggle criterion (28%, versus 90% required). |
| A2g-2 single-pair pool supply | **H2 NOT SUPPORTED; 809/810 complete** | 532/732 positive-down cells met the endpoint-isolation ratio (72.68%, versus 80%); 3,000-trial p* monotonicity passed in only 3/5 families. One external interruption was not retried. |
| A2g-3 `uk` + memory sampler | **H3 PASS** | All 90 operations and all 30 three-seed cells met the carried projection/mask criteria. |
| A2g-4 up/down conditioning | **Material distortion in 40/40 fine strata** | Every registered fine-stratum mean `D_trace` exceeded .05. Descriptive only, not causal or protocol evidence. |
| A2g-5 fixed-duration synthesis | **Offline proposal only** | Both fps grids pass the time-resolution screen and exact 12-second mean-up targets; legacy-pool evidence supports only a conditional candidate region, not a validated setting for the adopted pipeline. |

The cautious candidate for further offline planning is 120 seconds at either `(fps,F)=(1,120)` or `(2,240)`, with exact-quota `uk` targets, and legacy-pool `p_edge` points `.4` or `.5` only where a per-configuration supply preflight confirms strict quotas. This is **not** an A3 authorization or a claim of transfer to the adopted projected Markov sampler. A2g-1 and A2g-2 failures plus A2g-4 conditioning effects prohibit a broad claim that legacy pool behavior generalizes.

## Binding decisions and interpretation rules

- `uk` is adopted; request exact integer `(U,K)` and reject infeasible combinations with typed errors. Do not clamp or interpolate.
- Multipath is “single path, plus shared-source pairs as an exception.” MPC fail-closed remains proposal-only.
- Oracle: instantaneous per-frame usable S–R uptime, with no waiting. Time-respecting reachability is descriptive only and must explicitly say “allows store-carry-forward”.
- A2g-2 finite-pool supply means **distinct-entry** up/down quota capacity, not the legacy assembler's nonempty-pool requirement or its with-replacement assembly feasibility.
- Means and sample SDs use per-seed values with `ddof=1`. Per-seed rows remain preserved; do not treat repeated edges/frames as independent samples.
- Limits: one A1 graph realization per family/size; fixed structural-rule probe pairs; patched non-upstream memory sampler; timeline diversity family-independent by construction. The A2g-2 legacy iid pool source differs from the A2g-3 `uk` + patched-v3 path. A2g-4 A2f-3 versus A2g-3 source rows are not matched-seed comparisons.
- No causal, protocol-performance, or cross-family ranking claims. No A3, ns-3, or protocol variants. No `alpha/EM/` modification.

## Stage records

### A2g-1 — sampler provenance and edge flicker

Preregistered H1 required at least 270/300 successful A2c trace rows to have non-constraint-edge toggle probability within ±.05 of `2p(1-p)`. All 300 source traces passed integrity validation, but only **84/300 (28%)** met that numerical criterion; by p_edge, counts were .3: 25/100, .5: 25/100, .7: 34/100. This contrasts the A2c legacy iid finite-pool pipeline with A2f-3 `patched-v3` projected Markov traces and adopted `uk` timelines; it is provenance evidence, not an interchangeable-sampler claim.

Per-trace rows: [trace_metrics.csv](A2g-1/trace_metrics.csv). Summary: [result.md](A2g-1/result.md). Registration [a2g1_prereg.md](a2g1_prereg.md), SHA-256 `79ab901af5fd96912ea86a7d3ffed1b34decada1ac3e28f1635f2d52cb4346bd`; analyzer [analyze_a2g1.py](analyze_a2g1.py), SHA-256 `ce1f83bdc0cff07fbd8bca3ca243b1fb9fa548a9a6c83a87b74c6540f40b91ef`; result SHA-256 `20a6e85fbc9ac9dd62c7cd5c90763fb9ce05429d47a2014065f7dd1b9e100173`; trace metrics SHA-256 `75f710283216754d8537d97675726f59b01a75432cd44aa313283b32cbd261e`; summary JSON SHA-256 `fdade50b6973638ce5d3c16a45f75cf88098b3bb5d458eee5d80a760ed842604`.

Reproduction was a deterministic analysis of stored data: `/home/hledirach/Documents/J2/.venv/bin/python /home/hledirach/Documents/J2/simple-graph-experiments-v2/alpha/A2g/analyze_a2g1.py`.

### A2g-2 — single-pair up/down pool supply

The frozen grid was 15 A1 graphs × 9 p_edge values × 2 trial counts × 3 seeds = 810 operations. The parent sweep was externally interrupted before recording `er_N162_r1__p0.7__t10000__seed47`; that one cell remains missing and was not retried. The other 809 operation outputs remain successful. The registered endpoint-isolation criterion passed 532/732 positive-down cells (72.68%, below 80%). F=120 all-life p* monotonicity over N passed for 3/5 families at 3,000 trials and 4/5 at 10,000 (4/5 required at both); registered degree slopes passed. Overall H2 is **NOT SUPPORTED**, not rescued by the passing components.

Per-operation records and frozen configs: [operations](A2g-2/operations/); per-seed supply/readiness: [per_seed_supply.csv](A2g-2/per_seed_supply.csv); seed p*: [pstar_per_seed.csv](A2g-2/pstar_per_seed.csv); graph/trial summaries: [pstar_by_graph_trials.csv](A2g-2/pstar_by_graph_trials.csv); [operation_log.csv](A2g-2/operation_log.csv); [result.md](A2g-2/result.md). Registration SHA-256 `5e1ec283901728a9cf89f9a39dd6795c508793118e3a5c0329b6596a46247754`; frozen runner [run_a2g2.py](run_a2g2.py), SHA-256 `5359417fcb4737f907b8a04d3a6b0be10b9bf5b17d522ff48f33e66de9add5b1`; continuation [continue_a2g2.py](continue_a2g2.py), SHA-256 `a197ea2f7aaaeaab7bb2f93f92585197f81542375e1b4d339642b5ae6dae1fd4`; aggregation-only repair [aggregate_a2g2.py](aggregate_a2g2.py), SHA-256 `e28edd190cd19e49e48bb8cf78b5715f2b8256b4f4b83c5c2668ba298acbaa85`. Ledger SHA-256 `31c10ad4c1db5ce9664e5ac05920acf6c9441eb8d1e7ba672bef23fc6d35d451`; per-seed supply SHA-256 `d0cc3bd2d8d81315d684aeeae0b8702117ec0df198b6e8fec4121f0a4420eee1`; p* seed CSV SHA-256 `c4ae9e5de89ae93464514a6cb730eae91fc144d0585fcbb7028436e41ed254b1`; p* graph/trial CSV SHA-256 `e5daafe518c730508e56eab83f8d1449a851dbdfb61c0d9676109be1d02822df`; result SHA-256 `168138ea6333330c30f2deff91c441f11f06db9b647d06416a2f127cc841f2fb`.

Worker operations are historical and must not be replayed. Pool generation used the registered per-cell configs and isolated operations; the report-only aggregate command was `/home/hledirach/Documents/J2/.venv/bin/python /home/hledirach/Documents/J2/simple-graph-experiments-v2/alpha/A2g/aggregate_a2g2.py`.

### A2g-3 — `uk` with edge-memory sampler

The registered 5 graph × 2 life × 3 feasible parameter × 3 seed grid produced 90 operations / 30 three-seed cells. All 90 operations completed with exact `uk` U/K, exact instantaneous S–R masks, skeleton-only edges, edge-time projection fraction ≤.05, projected `|π̂−π|≤.05`, and projected completed up-duration relative error ≤.20. All 30/30 cells qualified, above the 27/30 threshold: **H3 PASS**. The mathematically infeasible `π=.8,L=2` cell was not run. Worst observed projection fraction `.0080314`, projected π error `.0122283`, and duration relative error `.1084264`.

Per-seed data: [per_seed_results.csv](A2g-3/per_seed_results.csv); cell and parameter summaries: [cell_summary.csv](A2g-3/cell_summary.csv), [parameter_summary.csv](A2g-3/parameter_summary.csv); operation outputs: [operations](A2g-3/operations/); [result.md](A2g-3/result.md). Registration SHA-256 `39247091532fdf0107c4fbfc9ff4b1297aa4eae46a1b0254177920357c44ce98`; frozen runner [run_a2g3.py](run_a2g3.py), SHA-256 `9660a8c0685332b2f9bf4db892e4583463743c01f075e02079d146b08ba5a209`; final aggregation-only helper [aggregate_a2g3.py](aggregate_a2g3.py), SHA-256 `6601471a5aff184999f5e96aad68ae4523bc29afc71a6d40b32bbb08caabd5c1`; result SHA-256 `306b3885fd89b69b64aae4739b41c77a4a5c66f1c6d82d8264f500f0b2692bb4`; summary JSON SHA-256 `993c1ff92367c08be0affc916da132b46dcb5513a09cf9271cb201cb8e86fa33`; artifact manifest SHA-256 `70b9615b892b9ed04c477e56d8da16d4922d31663fb1f1551c2e5d9396131a0b`.

Execution command was the frozen runner under `/home/hledirach/Documents/J2/.venv/bin/python`; aggregation-only command: `/home/hledirach/Documents/J2/.venv/bin/python /home/hledirach/Documents/J2/simple-graph-experiments-v2/alpha/A2g/aggregate_a2g3.py`. Do not replay worker operations.

### A2g-4 — up/down-conditioned background-edge distortion

The read-only analysis covered 50 stored A2f-3 traces plus all 90 A2g-3 traces (140 traces; 34,804 eligible edge×trace rows). Primary `D_trace` is the mean absolute background-edge availability difference between timeline-up and timeline-down frames. All **40/40** registered fine-stratum means exceeded the strict `.05` cutoff. Broad mean±sample SD: A2f-3 life .5 `.18559±.01745`, life .9 `.21874±.03412`; A2g-3 life .5 `.09665±.03249`, life .9 `.12766±.02299`. This is descriptive conditional dependence, not causal evidence; source groups are not matched-seed.

Per-edge rates: [per_edge_conditioning.csv](A2g-4/per_edge_conditioning.csv); per-trace effects: [per_trace_conditioning.csv](A2g-4/per_trace_conditioning.csv); fine strata: [fine_stratum_summary.csv](A2g-4/fine_stratum_summary.csv); pooled parameter rows: [parameter_summary.csv](A2g-4/parameter_summary.csv); [result.md](A2g-4/result.md). Registration SHA-256 `88c1b2a2378b31f95d6f6538113aed30f953ddd66226b14b42f1951653973e75`; final analyzer [analyze_a2g4.py](analyze_a2g4.py), SHA-256 `27b7aa2ee4ba5a092804ce769956b8bb700dcf6d258acee92cb934408882435a`; result SHA-256 `d1488ab78c143d6d2150fd2d7a3d58d17d2189eb138b4ed3757ae8ee27a423df`; per-edge SHA-256 `c26fb7ae3a4841890e1027332cf750dddd38cb5866d212760071fe800864041f`; per-trace SHA-256 `26d3071b75d6366065da2a23d98cbe0e9698237f76e2fe4d243449a113789387`; fine summaries SHA-256 `483265c42c4bf4145730c05a3a5f643fd0bb39246f67a36b32f5254bcd645b66`; broad summary SHA-256 `e469dfe6d742a465ea89518494bf408aa4ec85af447b1afffe25977208d376fc`; parameter summary SHA-256 `d737cdd39ae49205ff2b2bda9af8d0072df0b289abd41f225463497af14c37c3`; final input manifest SHA-256 `00f7faee9a7a0eff32ae0f3776a790185688c122d0a62a31c9e8cccc9851cd37`.

Deterministic command: `/home/hledirach/Documents/J2/.venv/bin/python /home/hledirach/Documents/J2/simple-graph-experiments-v2/alpha/A2g/analyze_a2g4.py`. The final analyzer added source/graph provenance and the preregistered pooled parameter table; this was reporting/provenance completion only and did not change observations, estimand, or cutoff. The final hash supersedes the initial analyzer hash recorded earlier in the gate log.

### A2g-5 — fixed-duration synthesis

Fixing 120 seconds gives `(1 fps,F=120)` or `(2 fps,F=240)`. Both frame lengths (1.0 s and .5 s) exceed the preregistered .32768 s screen (two 1024-byte intervals at 50 kbps). For each life `.3,.5,.7,.9`, a 12-second mean-up target is exact: `K={3,5,7,9}` at both frame grids. The 0.32768-second target is not in any exact `U/K` support, and no off-lattice interpolation was used.

Legacy-pool readiness counts at `p_edge=.4` and `.5` were 45/45 planned graph×seed cells at both F values and both trial sizes (3,000/10,000). The observed per-seed p* envelope was F=120: `.5–.7` at 3,000 and `.6–.8` at 10,000; F=240: `.5–.6` at 3,000 and `.5–.7` at 10,000. Because H2 did not pass and A2g-2 uses legacy iid pools, this only supports a cautious preflight candidate, not a universal guarantee or transfer to `uk`+patched-v3.

Full fixed-duration table: [fixed_duration_table.csv](A2g-5/fixed_duration_table.csv); graph/seed p* rows: [pool_support_by_graph.csv](A2g-5/pool_support_by_graph.csv); p-grid readiness counts: [pool_readiness_by_p.csv](A2g-5/pool_readiness_by_p.csv); [result.md](A2g-5/result.md). Registration SHA-256 `d3f4b27a5c70f8b4c888d412ae0ce71b8b3d981848fe0b5e42808348a9a6b9c0`; analyzer [analyze_a2g5.py](analyze_a2g5.py), SHA-256 `7fb6416cd0b5cac9e8d684ae06152f41bde3baff94bdd66d5a5871261ff47a02`; result SHA-256 `467e3c7b71941bb69a4414d313f3eedc43f49c23baaccc50865c6f9536ed1d14`; fixed-duration table SHA-256 `df5002121868d2f5f8c91e343cb99093bbe74af3a9f722d4b6bd8e73f597cb27`; pool support SHA-256 `8a43b9ffe55ee3d572af1380287f60053d36a33a835255bb28e78bee56d0f8ca`; readiness SHA-256 `b08ba704d00c8f4c07153ac46c43481cad465b40918a95d2596685e005ea8f3c`; input manifest SHA-256 `661f168cf16885a07e2d119a76439fe23d391aa1e268dd22a0958c188d511874`; artifact manifest SHA-256 `632c31e118142729b9068c190fa627d7e5b7864066c62a86ce0da250a9523e6d`.

Deterministic command: `/home/hledirach/Documents/J2/.venv/bin/python /home/hledirach/Documents/J2/simple-graph-experiments-v2/alpha/A2g/analyze_a2g5.py`.

## Final stop

All five A2g sub-stages are recorded; no numerical gate was relaxed, no missing operation was retried or imputed, and no prior/source artifacts were changed. The recommendation remains generator-only and conditional. **Stop at A2g. Do not start A3.**
