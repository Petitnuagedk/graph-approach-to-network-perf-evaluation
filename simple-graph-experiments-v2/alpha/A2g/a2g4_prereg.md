# A2g-4 preregistration — up/down background-edge conditioning distortion

Registered after A2g-3 H3 PASS was logged and before any up/down-conditioned background-edge group differences are calculated or compared. This is an offline analysis of stored A2f-3/A2g-3 frames only. No new frame generation, ns-3, protocol variants, or A3. Keep all outputs under `alpha/A2g/`; do not modify prior-stage files or `alpha/EM/`.

## Frozen trace set and edge eligibility

Use stored A2f-3 traces for all five fixed A1 N=92 graphs, lives `{.5,.9}`, target class `geometric_midpoint`, and all five registered seeds per life (50 traces total). This matches the A2g-3 exact timeline centers: F=120, U/K=`(60,5)` at life .5 and `(108,9)` at life .9, mean-up 12 frames. The A2f-3 traces use the earlier stored assembled-frame pipeline and are a descriptive historical comparison, not a randomized matched-seed arm.

Use all 90 stored A2g-3 feasible traces across the same five graphs/lives, `(π,L)={(.5,2),(.5,8),(.8,8)}`, and seeds `{11,29,47}`. Use the projected frame sequence (`projected_up`) because that is the delivered sequence whose S–R mask is constrained; retain raw-frame measures only as a secondary description if calculated. The infeasible `(.8,2)` condition is absent by design.

For each graph, reconstruct its canonical lexicographically smallest static shortest S–R path from the frozen A1 skeleton and probe pair. Eligible background edges are the skeleton edges that are (i) not incident to S or R and (ii) not on that canonical S–R path. Apply this same edge set to each source/trace of that graph. Verify nonempty eligible-edge set, 120 frames, exact expected up/down denominators, and edge provenance; integrity failure is not silently dropped.

## Estimand and frozen effect-size rule

For every eligible edge `e` in a trace, calculate its conditional availability difference:

`delta_e = mean(edge_e_up | timeline_up) − mean(edge_e_up | timeline_down)`.

The primary trace-level effect is the mean absolute conditional difference over eligible edges, `D_trace = mean_e |delta_e|`. Also report the signed mean delta, median and 90th percentile of `|delta_e|`, the fraction of eligible edges with `|delta_e| > 0.05`, and each edge's two conditional rates/counts. Do not treat edges within a graph or repeated frames as independent observations; report trace-level values and grouped descriptive means/sample SD (`ddof=1`).

Freeze **0.05 absolute conditional edge availability** as the practical material-distortion cutoff. This is aligned with the A2d item-1 per-trace projected marginal tolerance of 0.05: a mean absolute difference above this scale means conditioning on S–R state shifts background-edge availability by more than the previously accepted marginal-fidelity allowance. A source stratum is flagged for material conditioning distortion when its mean `D_trace` is strictly greater than 0.05; equality is not a flag. Compute A2f-3 strata by family×life (10 strata) and A2g-3 strata by family×life×π×L (30 strata). Also provide overall source/life and A2g-3 life/parameter summaries, but do not use those broad pooled means to suppress any flagged fine stratum. This cutoff is descriptive, not a hypothesis test or protocol gate.

## Provenance and outputs

Read A2f-3 `frames.csv`/`edges.csv` and A2g-3 `edge_states.csv.gz`, timeline and per-trace configs/results. Validate the selected A2f-3 traces have `uk`/`patched-v3`, requested U/K, and zero shortcut/instantaneous mask deviations; validate all A2g-3 operations are successful and exact-mask/skeleton-clean. Record paths and SHA-256 for each input artifact used, analyzer hash, per-edge conditional rates, per-trace effect rows, fine-stratum summary, broad summary, and a deterministic artifact manifest. No paired seed interpretation: the source seed sets differ and A2f-3 data were already fixed before this stage. No treatment, causal, inferential, or across-family ranking claims.

Carry all standing limitations: one graph realization per family/size; patched non-upstream sampler; timeline diversity family-independent by construction; fixed structural-rule probe pairs. Multipath remains “single path, plus shared-source pairs as an exception”; MPC fail-closed remains proposal-only. The operative oracle is per-frame instantaneous usable S–R uptime with no waiting. Any temporal reachability wording must say “allows store-carry-forward”. No A3/ns-3/protocol variants.
