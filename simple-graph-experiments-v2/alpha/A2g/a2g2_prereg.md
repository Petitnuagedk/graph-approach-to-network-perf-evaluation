# A2g-2 preregistration — single-pair up/down pool supply

Registered after A2g-1's H1 result and before generating any A2g-2 pool. This is offline generator-only work; no ns-3, protocol variants, or A3. All new code/configs/results stay under `alpha/A2g/`. Read-only inputs are the 15 A1 realization-1 edge lists (five families × N={42,92,162}) and each graph's frozen structural-rule probe S/R pair in `graph_covariates.csv`. One realization per family/size is a declared limitation.

## Frozen grid and operation policy

For each of the 15 graphs, generate one single-pair iid Bernoulli edge pool at each `p_edge` in `{.1,.2,.3,.4,.5,.6,.7,.8,.9}`, trial count in `{3000,10000}`, and pool seed in `{11,29,47}`: 15×9×2×3 = 810 independent operations. Use the A2d item-1 isolated donor's unchanged legacy `FrameGenerator.generateSPCFrames` behavior (or a count-only implementation proven draw-for-draw equivalent): an independent `random.Random(seed).random()` per skeleton edge per candidate; classify by S–R reachability and NetworkX shortest path; count each disconnected frame in the down pool and connected frames in shortest-path groups. No edge outside the skeleton is possible. Preserve all nodes, including isolates. Use one isolated child process per operation, 60-second wall timeout, no retries, no timeout extension, and no substitutions. Write each complete `config.json` before the child starts; save operation status and result or timeout/error for every registered cell. If an operation times out, continue other preregistered cells without replacing it.

## Measurements and supply definition

For each seed record up/down frame counts, number of distinct shortest-path groups among up frames, candidate-trial S–R connectivity fraction, `p_edge`, endpoint skeleton degrees `dS,dR`, shared endpoint-edge indicator, and the analytic endpoint-isolation probabilities:

- `P(S isolated)=(1-p)^dS`, `P(R isolated)=(1-p)^dR`;
- `P(both isolated)=(1-p)^(dS+dR-I[S~R])`;
- exact union bound/event probability `B_iso=P(S isolated or R isolated)=P(S isolated)+P(R isolated)-P(both isolated)`.

`B_iso` is an analytic lower bound on S–R disconnection, not a prediction of all disconnected components. Compare observed down fraction `f_down` to it only when `f_down>0`.

Supply-ready is deliberately a **strict finite-pool quota-capacity** criterion: a pool must have at least U distinct up-pool entries and D down-pool entries for the frame quota, despite the current assembler drawing with replacement. Report this separately from actual replacement-based assembly feasibility (which only requires nonempty pools). For F=120 and lives `{.3,.5,.7,.9}`, U=`round(F×life)` and D=F−U; per-life readiness is `up_pool>=U AND down_pool>=D`. “All-life p*” is the highest registered p_edge at which both U and D quotas are met for all four lives, equivalently `up_pool>=108 AND down_pool>=84`. Also calculate per-life demand/readiness at F=240, where U is `{72,120,168,216}` and D is `{168,120,72,24}`; all-life F=240 readiness requires `up_pool>=216 AND down_pool>=168`. No extrapolation beyond the registered p grid. For p* report seed-level values and mean/sample SD (`ddof=1`) over the three seeds; an absent qualifying p is `NA`, never clamped to .1 or .9.

Report per-seed rows and per graph×p×trial means/sample SDs of pool sizes/connectivity/groups and readiness, plus the A1 graph covariates (mean degree, diameter, dS/dR). Report for each family/size/trial the highest p satisfying all four lives, and the analogous F=240 value. Include descriptive OLS slopes of p* versus N, mean endpoint degree `(dS+dR)/2`, graph mean degree, and diameter, stating the sample unit and number of complete graph rows. Also list every family-size p* sequence; no significance claims and no across-family ranking.

## Numeric H2 decision rule

H2 is supported only if both registered components hold:

1. Among successful operation cells with positive observed down fraction, at least 80% have `1 <= f_down/B_iso <= 3` (equivalently the observed fraction is between the exact endpoint-isolation lower bound and three times that bound). A cell with zero down fraction is excluded only from this positive-down ratio denominator and remains in all pool/readiness tables. Any nonpositive analytic bound is a data-integrity failure; do not regularize it.
2. For F=120 all-life p*, after averaging defined seed-level p* values (`ddof=1` SD also reported), each of at least four of the five families has a non-increasing p* sequence over N={42,92,162} at **both** trial counts, and the pooled descriptive OLS slopes of p* versus mean endpoint degree and graph mean degree are each nonpositive. Undefined p* at any size makes that family/trial sequence fail this monotonic criterion. Diameter's slope is descriptive, not a gate.

All 810 operations must be successful and input/config/provenance integrity valid for a positive H2 verdict. Any timeouts are reported and count against completeness; do not change gates post-result. This design tests the candidate mechanism but does not guarantee support.

## Carried decisions / limits

`uk` is the adopted timeline interface for subsequent stages. For later assembled traces, the oracle is exact per-frame usable S–R uptime, with no waiting. Any time-respecting reachability result is descriptive only and explicitly labelled “allows store-carry-forward”. Multipath remains “single path, plus shared-source pairs as an exception”. The proposed MPC fail-closed adjustment remains proposal-only. Do not touch `alpha/EM/`. Report the known limitations: one graph realization per family/size; patched non-upstream generator; timeline diversity family-independent by construction; and fixed structural-rule probe pairs.
