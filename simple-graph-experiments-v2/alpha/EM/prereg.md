# A2e preregistration — isolated edge-Markovian fallback validation

Registered after the A2d item 3 result was logged and before any EM code or trace generation. This is a small generator-only fallback validation, not a YaDyGaGa extension, not an ns-3 run, and not a protocol variant. All files and outputs remain under `alpha/EM/`. Every output row carries generator label exactly `edge_markovian`; no figure series, table aggregate, or statistical model may pool this generator with YaDyGaGa.

## Generator definition and fixed design

Use A1 N=92 ER realization 1, fixed probe pair `(5,82)`, and 120 frames. Every skeleton edge receives an independent two-state Markov chain, initialized from stationary Bernoulli(π), with `P(1→0)=1/L` and `P(0→1)=π/((1−π)L)`. Edge chains use deterministic seed `base_seed + 104729*edge_index`, where graph edges are sorted lexicographically by integer endpoints. A requested cell is feasible iff both transition probabilities are in [0,1]. Never clamp infeasible inputs.

Requested grid: π ∈ {.5,.8}, L ∈ {2,8}, base seeds `{11,29,47,71,97}`. This yields 20 grid/seed records. Analytic feasibility check identifies π=.8,L=2 as infeasible (`P(0→1)=2`); record its five seed rows as `not_run_infeasible`, do not instantiate/generate chains for them, and report no substitute values. Run the 15 feasible condition/seed operations, each in a separate process and isolated output folder. Write a full config before each child operation; each operation has a 60-second timeout, no retries or replacements.

Persist all edge state strings, the per-frame assembled graph edge lists/fingerprints, and the actual S–R route/up-down trace. For each generated trace report edge-pooled up fraction; mean completed up-run duration using only runs bounded by a down state on both ends; edge-level transitions; S–R uptime, up-run lengths, transitions, first outage, and per-frame shortest-path hop count (NA when down). Mark all records with generator label `edge_markovian`. Output requested edge π and L separately from realized S–R lifetime; S–R uptime is an outcome and is not forced to equal π.

## Numeric gates

1. **Analytic feasibility:** all 20 records correctly classify exactly 15 feasible operations and five π=.8,L=2 infeasible records. Infeasible records generate no random values, are not clamped, and contain no fabricated trace metrics.
2. **Completion and provenance:** 15/15 feasible operations complete within 60 seconds without retry; every frame is a subgraph of the hashed ER skeleton; fixed pair and N are unchanged.
3. **Edge marginal gate:** for each feasible operation, absolute error between pooled realized edge-up fraction and target π is <=.02.
4. **Edge persistence gate:** for each feasible operation, absolute relative error of the pooled fully completed edge-up-run mean versus L is <=.05. Report censored boundary runs separately and exclude them from this estimator.
5. **Reporting integrity:** all 20 records contain `generator=edge_markovian`; all 15 feasible operations save S–R per-frame statuses/routes/hops, uptime, up runs, transitions, and first outage. S–R quantities are descriptive outputs with no pass threshold because EM does not constrain route uptime.

Report the 5 seed-level statistics and condition-level mean/sample SD (`ddof=1`) separately for each feasible `(π,L)` cell. No cross-generator comparisons, pooled estimates, or mixed plots. This validates only these N=92 graph, probe, horizon, and parameter cells; it does not authorize broader EM use. No ns-3, 0 protocol variants, no A3.
