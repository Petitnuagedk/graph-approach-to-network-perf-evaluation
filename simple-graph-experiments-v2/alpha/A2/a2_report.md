# Alpha A2 consolidated report

**Disposition:** A2’s registered generator-only investigations are reported here. The YaDyGaGa path is not extended beyond the isolated A2d item 1 patch, and the separate edge-Markovian fallback test failed two frozen numeric gates. A2d item 4 remains proposal-only. Stop at A2: no A3, ns-3, protocol variants, or cross-generator pooling.

## Binding design decisions and scope

The main [A2 preregistration](prereg.md), SHA-256 `a33fbd0acc7d9666a164bc4f0ad3f4880b223267e09c4959ee74134d4d40266c`, records the initial scope and explicit correction that only uptime and requested $K$ are fixed by construction. Subsequent stage decisions, amendments, and append-only outcomes are listed in [the Alpha gate log](../gates.md).

- Retain the A1 structural S–R pair rule and its fixed pairs; do not select pairs based on A2 outcomes.
- Exact uptime quota $U$ and requested positive up-run count $K$ are fixed by construction. Total transitions depend on the sampled down-run/boundary arrangement and are measured per trace, not claimed fixed.
- Compare Boolean-schedule diversity by maximization against the exact-uniform feasible-schedule baseline, rather than an absolute diversity threshold.
- Select stability per life using the preregistered A2a rule.
- Keep edge-Markovian strictly fallback-only, isolated under [the EM directory](../EM/), and label every result `edge_markovian`. It is not YaDyGaGa, must not share plots or statistical summaries with YaDyGaGa, and cannot be used to rescue a failed YaDyGaGa gate.
- All sample standard deviations in A2 use `ddof=1`. The separate legacy plotting utility's population-SD convention is not used for these registered summaries.
- Total protocol variants: **0**. No ns-3; no A3.

## Gate summary

| Stage | Outcome | Main finding |
|---|---|---|
| A2a feasibility/stability map | PASS | All 567 grid rows and 81 stability-rule rows computed; exact counts independently matched. |
| A2b Boolean schedule diversity | PASS for registered Level 1 | All 800 candidate labels generated; four life cells exceed 0.90× exact-uniform $E[D]$ and satisfy support/duplicate gates. |
| A2c dynamic traces | PASS | All 300 traces complete; all masks/fidelities and all 20 route-diversity cells pass. |
| A2d item 1 edge-memory sampler | PASS | 172/172 operations pass; isolated source patch and exact patch artifact are recorded. |
| A2d item 2 original attempt | FAIL operationally | Probe helper raises `KeyError` for ID-labeled status tuples; no valid fidelity/capacity conclusion. |
| A2d item 2 correction v1 | Operational PASS; fidelity arrangement-dependent | Shared-source passes 42/42; disjoint passes only 3/42, failing already at $m=2$. No general capacity limit. |
| A2d item 3 reproducibility | PASS for tested seeded pipeline | 15/15 exact hashes, exact masks, skeleton provenance; archived unseeded legacy assembler not tested. |
| A2d item 4 | PROPOSAL ONLY | Exact Boolean feasibility boundary and proposed `(U,K)` interface; no code or test without approval. |
| A2e edge-Markovian fallback | FAIL under frozen numeric gates | 15/15 feasible operations complete, but marginal fails 1/15 and completed-duration gate fails 8/15. Reporting-gate bookkeeping was corrected append-only; overall FAIL is unchanged. |

## Stage results

### A2a — exact feasibility and per-life stability choice

The finite-trace map contains 567/567 rows; exact up/down-run counts matched an independent factorial implementation. All 81 stability-rule rows were written. For $F=120$, the registered A2c defaults are:

| Life | Stability | Requested up-runs $K$ |
|---:|---:|---:|
| 0.3 | 0.3 | 26 |
| 0.5 | 0.5 | 30 |
| 0.7 | 0.7 | 26 |
| 0.9 | 0.9 | 12 |

All four selected cells are feasible and mean up-run length is at most 30 frames. At life 0.9, only stability at least 0.9 is feasible on the registered 0.05 grid. See [A2a preregistration](A2a/prereg.md) and the append-only A2a result in [the gate log](../gates.md).

### A2b — schedule diversity relative to exact-uniform baseline

All 800 candidate labels (200 schedules per life × four lives, joined across the five family names) completed without timeout or retry. Each cell had 200/200 unique schedules and largest duplicate group 1. Exact-uniform Monte Carlo used 100,000 independent schedule pairs per life; all standard errors were below 0.002. Greedy-5 mean normalized diversity $D$ and ratio to exact-uniform $E[D]$ were: life 0.3, 0.775000 / 1.1071; 0.5, 0.556667 / 1.1130; 0.7, 0.761111 / 1.0867; 0.9, 1.000000 / 1.1115. All Level 1 gates pass. The route-sequence Level 2 requirement was evaluated separately in A2c.

See [A2b result](A2b/results/result.md), final logged SHA-256 `4e38f5e13fa8cef72624594949b9350e517e91b47ccf3e11aa9ae252ccc5f869`, and [A2b preregistration](A2b/prereg.md), SHA-256 `6937f222df17c3b604deb2e04ada075f597aeb47a132fae51597883be9dd78a1`.

### A2c — dynamic-trace characterization

All 300/300 child operations completed under their 60-second limits; no retries, empty required pools, fidelity-mask mismatches, or shortcuts. All traces had exact A2a $U/K$, supported transition counts, skeleton-only edges, exact requested usable uptime, and nonempty pools. The 20 life×seed schedules matched A2b and were identical across graph families and edge-density settings. All 20 family×life canonical route-diversity cells passed 10/10 distinct pairs against the 9/10 threshold. Registered time-respecting reachability at $p_{edge}=0.5$ ranged 0.856667–0.970000; these are time-expanded-graph measurements, not packet delivery or instantaneous connectivity.

See [A2c result](A2c/results/result.md), SHA-256 `c137f32b205c62c1df96b44b38c2470fb44c9962abb1285fd23d1233eb373d37`, and [A2c preregistration](A2c/prereg.md), SHA-256 `c91eb2227401ff56334bf6ea875e19b7ea3744e8d34bf7435b880326db745172`.

### A2d item 1 — isolated per-edge memory sampler

The registered item passed 172/172 operations: 12 standalone chains, 60 S–R integrations, and 100 legacy-compatibility checks. All standalone and integrated numeric gates passed; all target S–R masks were exact and all output edges were in their skeleton. Projection did produce small nonzero shifts to edge statistics; raw and projected statistics remain separately reported.

The validated source remains an isolated copy. Its current result report is [A2d item 1 result](A2d/item1/results/result.md), SHA-256 `e56c1cbe9278d48f09345d1435f3bf8c35e3ae1e6574fafca9c777f4760fd338`. The exact baseline-to-result patch is packaged in [the patch payload](A2d/item1/frameGenerator.patch.gz.b64); the decompressed unified-diff SHA-256 is `16052d4777996aa6e7b3a09cf5de7fac6707242e340dfa74d669db58dd66ffc7`, and its dry-run against the baseline passed without mutation. Patch instructions and hashes are in [source_patch.md](A2d/item1/source_patch.md). This is a generator diagnostic only—not Beta or protocol authorization.

### A2d item 2 — MPC probe: preserve both attempts distinctly

The original registered attempt launched 18 operations, all failing in the legacy helper/serialization path; this is a probe incompatibility, not evidence of an MPC scale limit. Preserve the original failure report and its correction: six $m=2$ cases raised a `KeyError` in `computeStatistics()`, while twelve $m=4/m=8$ cases assembled and then failed during JSON serialization of mixed `None`/integer tuple keys.

Correction v1 was separately preregistered and replayed the exact 18 cells/seeds into a separate results tree. It completed 18/18 operations without retry. Shared-source pairs met per-pair fidelity at $m=2/4/8$ (6/6, 12/12, 24/24). Disjoint pairs passed only 3/42 (1/6 at $m=2$, 2/12 at $m=4$, 0/24 at $m=8$). Disjoint fidelity therefore fails even at $m=2$; do not infer a general pair-capacity limit. The valid correction results are not pooled with the original failed attempt.

See the [item 2 result](A2d/item2/results/result.md), correction v1 report SHA-256 `de557311254e4fc375cdbc125ab0b50e36dfbe1724ee238e838fdf874d9fa26d`, original preregistration SHA-256 `dd0cce3b58db29079d697640243e4e8ac9ca6b948b5a3191dd223d3730f233b8`, and [correction v1 preregistration](A2d/item2/correction_v1_prereg.md), SHA-256 `4ec08bbf625b39d9164203c488af193b0fd1a582b480e1bda5cdaccda09a2794`.

### A2d item 3 — seeded pipeline reproducibility

Ten isolated child processes (five seeds × two independent runs) completed under 60 seconds. Timeline, full ordered pool, and assembled-frame hashes matched 15/15 comparisons; all ten S–R masks were exact, all pools nonempty, and all edges were in the fixed skeleton. This finding is limited to the tested seeded isolated path, Python 3.14.4, NetworkX 2.8.8, N=92 ER realization 1, pair (5,82), and registered parameters. The archived legacy unseeded assembler was not executed.

See [item 3 result](A2d/item3/results/result.md), SHA-256 `4cb37b40d18f1127c4888072bf412ce53ac85fb88c4162d4b8e97b120e511df1`, and [item 3 preregistration](A2d/item3/prereg.md), SHA-256 `216484c5425c1518feb0e9a4926431923a9a4cd81315219ec89079d7c2baddfc`.

### A2d item 4 — proposal only; approval required

The proposal notes a structural support limit for binary traces: with $U$ up frames, $D=F-U$ down frames, and $K$ positive up-runs, $1 \le K \le \min(U,D+1)$. It recommends explicit `(U,K)` controls with a typed infeasibility result, not clamping, while retaining a legacy stability adapter if a future isolated prototype is approved. No item 4 source or experiment was created. See [proposal](A2d/item4_proposal.md), SHA-256 `9ea71469adefa5c2865afc6f87146d305f4c4636f0a42fd171f1a114eb133cf7`. Do not implement without user approval.

### A2e — isolated `edge_markovian` fallback validation

The registered grid had 20 seed/cell rows: 15 feasible operations and five analytically infeasible `π=.8,L=2` rows. The infeasible rows were not sampled. All 15 feasible operations completed in separate processes within 60 seconds, with no retries; all frame edges remained in the hashed ER skeleton.

The frozen edge-marginal absolute-error gate (`<=.02`) failed in 1/15 operations: `π=.5,L=8,seed=47` had error 0.0201603. The frozen completed-edge-up-duration relative-error gate (`<=.05`) failed in 8/15 operations, all in feasible $L=8$ cells; maximum was 0.0764242 at `π=.8,L=8,seed=11`. Thus A2e is **FAIL**, not a passing fallback qualification. S–R lifetime, routes, hops, transitions, and outage are descriptive outputs and were not forced to equal the requested edge marginal.

The initial aggregate mistakenly marked the reporting gate false because it required trace metrics on infeasible rows. An append-only correction established that the label is present on all 20 records and all required files exist for the 15 generated traces; reporting integrity is PASS. This bookkeeping correction does not change either failed numeric gate or A2e's overall FAIL. The initially emitted [result report](../EM/results/result.md), SHA-256 `4fd28b21b4b409837074b24863c6f390b236636a6d2b85878c527ee647e6ad6e`, is retained unchanged; read it together with [the reporting correction](../EM/results/reporting_gate_correction.md), SHA-256 `1a0513758b5043f5b65450fa7cef27f2107ae6c0454738b5c204d2f8897d9251`, and [corrected gate summary](../EM/results/gate_summary_corrected.json), SHA-256 `857821a2be925a7437e6ac7ea960a1f744fe4873bf8295546b252a0185a294b3`. The [preregistration](../EM/prereg.md), SHA-256 `7d0363b2b74ca247acf4fbbf3cfe5f8be03fda0adf3e1766d2c3a7471983a408`, and execution runner hash `e5a923dca653c821fb623a7be714f517c7109210cc009726157e3006fc17498c` remain distinct from YaDyGaGa artifacts. Do not pool, compare, or plot these fallback traces with YaDyGaGa.

## Final boundary

The A2 ledger is complete through the preregistered A2e fallback check. A2d item 4 remains an unapproved proposal; A2e failed its fixed marginal and duration tolerances. Preserve the original item 2 failure and the separate correction, and preserve the original A2e aggregate together with its reporting-only correction. No threshold was relaxed, no variant or replacement trace was added, and no historical Alpha result was rewritten. Stop at A2 pending user direction: **0 protocol variants, no ns-3, no A3**.
