# A2a preregistration — exact feasibility and stability-selection map

**Registered 2026-10-09 before calculating any A2a map values.** New numerical decision thresholds in this protocol are **written after A0-R2 results**. This is an offline integer/formula computation only: no timeline generation, frame sampling, trace assembly, ns-3, or protocol variants.

## Registered formulas and grid

Use exactly the A0-R2 formula for each frame count F, requested life q, and stability s:

- `U = round(F*q)` using Python's round-to-even integer semantics; `D=F-U`.
- `K=round(1+(1-s)*(U-1))`, clamped to `1..U` for U>0; for U=0 define K=0.
- Exact feasibility iff `K <= D+1` (with trivial U=0/F cases feasible with singleton support).
- For 0<U<F and feasible K, `M = C(U-1,K-1) * sum_{J=max(1,K-1)}^{min(D,K+1)} b(K,J)*C(D-1,J-1)`, where b=2 for J=K and 1 for J=K±1. If infeasible M=0; all-up/all-down M=1.
- For nontrivial timelines, supported down-run count J spans that same inclusive range and the number of Boolean transitions is `K+J-1`; report the min/max over J. Trivial schedules have 0 transitions.

Compute the complete Cartesian grid `F={60,120,240}`, `q={0.1,0.2,...,0.9}`, `s={0,0.05,...,1}`. Required map size: exactly `3*9*21=567` rows. Save integer M and `log10(M)` (use `-inf` for M=0), plus U,D,K,J range and transition range. No feasibility interpolation or relaxation.

## Candidate stability rules and default choice

For each `(F,q)`:

1. `s_min`: lowest grid stability with exact feasibility. Report its K, M, log10 M, mean up-run `U/K`, J and transition ranges. If no grid stability is feasible, report `NONE` and do not select an A2 cell at that life/F.
2. `s_div`: feasible grid stability maximizing exact `log10(M)` (equivalently M); exact ties select lowest s. Report the same fields. If no stability is feasible, `NONE`.
3. `s_max`: largest grid stability with K=1, reported for contrast with same metrics. It is not a default candidate.

The default decision rule is preregistered now: use `s_div` unless its mean up-run duration `U/K` is **greater than 30 frames**, i.e. 25% of the A2c 120-frame horizon; if it exceeds 30, use `s_min`. If `s_min` is infeasible (not expected for selected A2c lives), mark no feasible default and stop rather than relaxing. The 30-frame cutoff is **written after A0-R2 results** and fixed before map computation. Apply the rule separately for each F and life; A2c uses only F=120.

Report for each F the exact life range / grid cells with no feasible stability, including any highest feasible stability and corresponding K, so users can see the triangular region. Gate A2a passes only if all 567 rows and all 27 candidate-rule rows are present, every computed M agrees with direct enumeration for all F<=60 parameter cells (enumeration of 2^60 is impossible; therefore the small-check is instead a deterministic independent closed-form cross-check that recomputes the binomial sum by a second implementation for every F=60 grid row), every selected stability satisfies its rule, and all hashes are logged in `alpha/gates.md` before A2b starts. No criterion may be relaxed after computation.

## Output and stop rules

Write map, rule comparison, and per-F life feasibility summaries under `alpha/A2/A2a/results/`. Record implementation command, Python version, and hashes. If any selected life at F=120 has no feasible stability, stop before A2b/A2c and ask. No protocol variants are spent.
