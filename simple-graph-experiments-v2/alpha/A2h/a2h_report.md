# Alpha A2h result — offline only

**Disposition: H1 PASS; H2a exact-mask completeness FAIL; carried tolerance gate PASS at both N.** This report records no ns-3 execution and 0 protocol variants. A2h does not authorize A3 or Beta.

## Registered scope and execution

- A2h-1 recomputed the A2g-4 statistic for 140 stored traces and enumerated all 119 nonzero circular shifts per trace (16,660 null values). All recomputed observed statistics matched their prior values; all 20 source×family×life cells were classified under the frozen rule.
- A2h-2 used fps=1, F=120, the `uk` timeline overlay and A2d item-1 `FrameGenerator` in read-only source copies. Of 1,440 design rows, 450 were analytically/quota-infeasible and correctly not launched; all 990 feasible operations were traversed. Results: 989 successful, one unresolved under the registered no-retry rule.
- The unresolved operation is `er__N162__life0.7__m24__pi0.5__L2s__seed43`. Its launch marker existed without a result. It remains `unknown_interruption_no_retry`; it was not relaunched and is not counted as a shortcut.
- The chain grid originally used the preregistration hash recorded in its operation configs. An append-only accounting clarification was added after the interruption and before the separate missing-pool operation; it documents the no-retry disposition and aggregation/path corrections, without changing design or thresholds.
- The one authorized missing A2g-2 cell (`er_N162_r1`, p=.7, 10,000 trials, seed 47) completed successfully. It replaces the existing seed-47 p* contribution; it does not increase the seed denominator.

## A2h-1 circular-shift result

Classification is “real conditioning” only when mean excess >.05 and at least ceil(2n/3) traces have empirical p<.05. Means below list mean D_obs / mean circular-shift null, followed by classification. Full per-trace and per-shift values are in [A2h-1 outputs](A2h-1/).

| Source | Family | Life | Mean D_obs | Mean null | Classification |
|---|---|---:|---:|---:|---|
| A2f-3 | ba | .5 | .18581 | .10703 | real conditioning |
| A2f-3 | ba | .9 | .21811 | .13145 | real conditioning |
| A2f-3 | er | .5 | .18548 | .10667 | real conditioning |
| A2f-3 | er | .9 | .21842 | .13162 | real conditioning |
| A2f-3 | geodesic | .5 | .18609 | .10715 | real conditioning |
| A2f-3 | geodesic | .9 | .21995 | .13151 | real conditioning |
| A2f-3 | rgg | .5 | .18520 | .10714 | real conditioning |
| A2f-3 | rgg | .9 | .21809 | .13147 | real conditioning |
| A2f-3 | ws | .5 | .18540 | .10728 | real conditioning |
| A2f-3 | ws | .9 | .21911 | .13196 | real conditioning |
| A2g-3 | ba | .5 | .09670 | .09957 | not resolved above null |
| A2g-3 | ba | .9 | .12702 | .12888 | not resolved above null |
| A2g-3 | er | .5 | .09588 | .09948 | not resolved above null |
| A2g-3 | er | .9 | .12768 | .12890 | not resolved above null |
| A2g-3 | geodesic | .5 | .09655 | .09959 | not resolved above null |
| A2g-3 | geodesic | .9 | .12728 | .12883 | not resolved above null |
| A2g-3 | rgg | .5 | .09735 | .09951 | not resolved above null |
| A2g-3 | rgg | .9 | .12774 | .12884 | not resolved above null |
| A2g-3 | ws | .5 | .09677 | .09965 | not resolved above null |
| A2g-3 | ws | .9 | .12856 | .12897 | not resolved above null |

Consequence statements, without causal attribution: **A2f-3:** Background traffic should be treated as S–R-state-conditioned in the flagged family/life cells; no causal mechanism is identified. **A2g-3:** This test did not resolve conditioning above the circular-shift null; it does not establish conditional invariance.

## A2h-2 chain feasibility and coverage

| N | Launched | Exact mask and U/K | Joint carried tolerances | Shortcut observations | Gate outcome |
|---:|---:|---:|---:|---|---|
| 92 | 495 | 495/495 (100%) | 495/495 (100%) | 0 nonzero / 495 complete | Exact and tolerance gates pass |
| 162 | 495 | 494/495 (99.798%) | 494/495 (99.798%) | 0 nonzero / 494 complete; 1 unresolved | Exact gate fails; tolerance gate passes |

All successful operations passed each carried tolerance separately: projection correction <=.05, projected all-skeleton-edge |π̂−π| <=.05, and projected completed up-duration relative error <=.20. Per-N/family/(π,L) counts for each individual tolerance and exact-mask result are in [the stratified table](A2h-2/tolerance_by_N_family_parameter.csv); per-seed metrics are in [the operation table](A2h-2/per_seed_results.csv). The 90% joint-tolerance minimum passes at both N. No nonzero shortcut was observed among completed operations; the one unresolved outcome remains unknown, not evidence of zero shortcut. Strict exact-mask completeness over all 990 feasible operations fails at 989/990. The standalone A2d item-1 thresholds (π error <=.02, duration error <=.10) are stricter than the carried A2g-3 integrated thresholds and are descriptive comparisons only; they do not replace the registered gate.

The feasible chain parameter pairs were (.5,2 s), (.5,8 s), and (.8,8 s); (.8,2 s) was analytically infeasible and not run. This is a tested feasibility region for the registered grid, not a general operating-region claim.

## Missing A2g-2 pool cell

The completed pool had 9,961 up and 39 down frames out of 10,000. Strict all-life pool readiness at p=.7 was false for both F=120 and F=240; the updated seed-47 p* contribution is .6 for both horizons. The 10,000-trial monotonicity count remains 4/5 families (ER is non-monotone). See [cell result](A2h-2/missing_pool_cell_result.csv) and [monotonicity update](A2h-2/pstar_monotonicity_update.csv).

## Gate table

| Gate | Frozen threshold | Observed | Verdict |
|---|---|---|---|
| H1 null-analysis integrity | 140 traces, 119 shifts each; all 20 cells classified | 140/140; 16,660/16,660; 20/20; prior D recomputations match | PASS |
| H2a exact-mask completeness | 100% of 990 feasible operations | 989/990; one unresolved no-retry interruption | FAIL |
| H2a joint carried tolerances | >=90% at each N | N=92: 495/495; N=162: 494/495 (99.798%) | PASS |
| Shortcut stop-critical check | No nonzero shortcut in completed operations | 0/989; 1 operation unresolved | No observed failure; unresolved |
| Missing-cell completion | One registered cell, no retry | One success; seed 47 replaced, denominator remains 3 | PASS |

## Deviations, limits, and decisions

The post-run `timeline_seed` aggregation-key defect and missing-pool reader-path defect were corrected in the summarizer; stored operations were summarized without relaunch. The interruption, no-retry accounting, and seed-47 replacement clarification are recorded append-only in the preregistration. No thresholds, seeds, or operation data were changed. No family ranking or ceiling claim is made. See [shared Alpha limitations](../LIMITATIONS.md).

**Decision requested:** confirm or reject the provisional `uk` + per-edge memory-chain sampler for Beta, and whether to carry only the tested feasible `(π,L)` pairs forward; decide whether the A2f-3 conditioning result warrants drafting (not implementing) a mitigation proposal. A2h does not authorize protocol variants, ns-3, A3 edits, or A4.
