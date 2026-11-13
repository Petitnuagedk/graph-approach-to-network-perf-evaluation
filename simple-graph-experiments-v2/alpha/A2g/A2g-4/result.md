# A2g-4 result — up/down background-edge conditioning distortion

## Disposition

**Material conditioning distortion was observed in every registered fine stratum: 40/40 exceed the preregistered 0.05 cutoff.** This is a descriptive effect-size classification, not a hypothesis test or a protocol-performance result. The analysis covered 50 stored A2f-3 traces and all 90 A2g-3 traces (140 total), with 34,804 eligible edge×trace rows. The exact S–R target mask, fixed structural-rule pair, path exclusion, and graph edge provenance were validated; no new frames were generated.

For each eligible background edge, the per-trace conditional difference is edge availability in timeline-up frames minus availability in timeline-down frames. The primary trace effect `D_trace` is the mean absolute difference over eligible edges. Fine-stratum classification uses the mean of `D_trace` across the traces in that stratum; material distortion is `>0.05` absolute availability. Sample SDs use `ddof=1` across traces.

## Source-level summaries

| source | life | traces | mean `D_trace` ± sample SD | max `D_trace` | fraction of eligible edge-trace rows with absolute delta > .05 |
|---|---:|---:|---:|---:|---:|
| A2f-3 stored assembled frames | .5 | 25 | .18559 ± .01745 | .20371 | .8302 |
| A2f-3 stored assembled frames | .9 | 25 | .21874 ± .03412 | .26444 | .8740 |
| A2g-3 projected memory frames | .5 | 45 | .09665 ± .03249 | .15357 | .6480 |
| A2g-3 projected memory frames | .9 | 45 | .12766 ± .02299 | .17177 | .7523 |

These are not matched-seed or randomized source comparisons. A2f-3 and A2g-3 use different registered seed sets and different frame-pool/projection paths; report the numbers as an across-source descriptive contrast only. In A2g-3, all six life×(π,L) strata also exceed the cutoff across families (n=15 each):

| life | π | L | mean `D_trace` ± sample SD | max |
|---:|---:|---:|---:|---:|
| .5 | .5 | 2 | .06683 ± .00232 | .07066 |
| .5 | .5 | 8 | .14052 ± .00740 | .15357 |
| .5 | .8 | 8 | .08261 ± .00562 | .09202 |
| .9 | .5 | 2 | .11819 ± .00275 | .12309 |
| .9 | .5 | 8 | .15796 ± .00971 | .17177 |
| .9 | .8 | 8 | .10681 ± .00377 | .11345 |

The A2f-3 family×life fine strata range from mean `D_trace` .18520 to .21995 and all flag; the A2g-3 family×life×π×L strata range from .06585 to .16080 and all flag. Complete fine-stratum rows are in [fine_stratum_summary.csv](fine_stratum_summary.csv). The conditional contrast is largest at long edge-memory L=8 within both lives for the tested parameter grid; the unrun infeasible `(π=.8,L=2)` condition is not inferred or imputed.

## Interpretation

The cutoff is the A2d item-1 .05 per-trace projected marginal tolerance, repurposed before analysis as a practical scale for an up/down-conditioned background-link availability difference. All observed fine-stratum means exceed that scale. This establishes that, in these stored traces, non-endpoint/non-static-path background edges are not conditionally invariant between the two S–R states. The effect is smaller in A2g-3 than in the stored A2f-3 assembled traces on the selected cells, but remains material in every tested A2g-3 stratum. It does not show that one sampler causes the difference: the traces are not matched-seed/randomized and differ in generation/assembly procedure. This is not a protocol oracle and should not be interpreted as routing performance.

## Artifacts and identities

- Preregistration: [a2g4_prereg.md](../a2g4_prereg.md), SHA-256 `88c1b2a2378b31f95d6f6538113aed30f953ddd66226b14b42f1951653973e75`.
- Final analyzer: [analyze_a2g4.py](../analyze_a2g4.py), SHA-256 `27b7aa2ee4ba5a092804ce769956b8bb700dcf6d258acee92cb934408882435a`.
- [Per-edge rates](per_edge_conditioning.csv), SHA-256 `c26fb7ae3a4841890e1027332cf750dddd38cb5866d212760071fe800864041f`.
- [Per-trace effects](per_trace_conditioning.csv), SHA-256 `26d3071b75d6366065da2a23d98cbe0e9698237f76e2fe4d243449a113789387`.
- [Fine-stratum summaries](fine_stratum_summary.csv), SHA-256 `483265c42c4bf4145730c05a3a5f643fd0bb39246f67a36b32f5254bcd645b66`.
- [A2g-3 life×π×L summary](parameter_summary.csv), SHA-256 `d737cdd39ae49205ff2b2bda9af8d0072df0b289abd41f225463497af14c37c3`.
- [Broad source/life summary](broad_summary.csv), SHA-256 `e469dfe6d742a465ea89518494bf408aa4ec85af447b1afffe25977208d376fc`.
- [Summary JSON](summary.json), SHA-256 `aee4177e4b249241e014ab5ce8bfa74e4fa4bf80e774aa8b30d80d8e5408d906`.
- [Input manifest](input_manifest.csv), SHA-256 `00f7faee9a7a0eff32ae0f3776a790185688c122d0a62a31c9e8cccc9851cd37`.
- [Output manifest](artifact_manifest.csv), SHA-256 `d0021b9334d722a3abb6679bb5ae9a5a5eced5fd51e71c36f22609e57e4da7d0`.

The first deterministic analyzer output omitted graph edge lists and source index/ledger files from the input manifest. The analyzer was amended to include those provenance inputs and the preregistered A2g-3 parameter summary; the calculation and frozen cutoff were unchanged. The final analyzer hash and final manifests above supersede the initial analysis artifacts. All 140 trace metrics and source/config identities were revalidated.

## Limits

One A1 graph realization per family/size; fixed structural-rule probe pairs; patched non-upstream sampler; timeline diversity family-independent by construction. A2f-3 target traces use only its geometric-midpoint condition at life .5/.9. A2g-3 uses only the three feasible registered `(π,L)` values. Multipath remains “single path, plus shared-source pairs as an exception”; MPC fail-closed remains proposal-only. The operative oracle remains instantaneous per-frame S–R uptime with no waiting. Any temporal-reachability wording must explicitly say “allows store-carry-forward”. No ns-3, protocol variants, or A3.
