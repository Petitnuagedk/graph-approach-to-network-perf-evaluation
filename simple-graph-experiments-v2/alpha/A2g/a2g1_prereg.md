# A2g-1 preregistration — stored-trace sampler provenance and edge flicker

Registered before opening stored edge traces for calculation. Generator-only/offline; no ns-3, no protocol variants, no A3. This analysis reads only existing A2c and A2f-3 artifacts; it does not modify them.

## Questions and frozen scope

1. Establish sampler provenance from each stored `config.json`, its source hashes, and the exact generation call in the corresponding runner/source. A2c is the legacy per-frame Bernoulli pool path unless evidence contradicts it; A2f-3 declares `frame_behavior=patched-v3` and `timeline_behavior=uk`. Report source-level mechanism separately from observed artifact metrics.
2. Estimate adjacent-frame edge toggle probability for every stored successful A2c trace (five families × four life values × five seeds × three `p_edge` values = 300 trace rows). For a Bernoulli-edge baseline, compare with $q(p)=2p(1-p)$.
3. Describe the same toggle statistic for every successful stored A2f-3 trace (five families × four lives × three target classes × five seeds = 300 rows), but do not test it against $2p(1-p)$ because these are memory-chain frames followed by S–R projection, and the artifact p-axis denotes stationary edge occupancy, not independent Bernoulli resampling.

A constraint edge for this analysis is any edge on the lexicographically canonical static shortest S–R path in the registered A1 skeleton. Exclude these edges from the primary non-constraint toggle denominator in both grids, as a conservative common structural exclusion. Also report all-edge and excluded-edge toggles separately. A2c has no explicit edge-level S–R projection; this exclusion is still retained for comparability. For each trace, toggle probability is the count of edge state changes across the 119 adjacent frame boundaries divided by 119 × the number of edges in the selected edge set. Edges absent from a frame are treated as state 0. No transitions are formed between distinct traces.

## Numeric gate and inference

**H1 passes iff at least 90% of the 300 successful A2c family×life×seed×p rows have absolute deviation $|q_{observed}-2p(1-p)|\le 0.05$** on the primary non-constraint edge set. The expected value is the independent-frame Bernoulli baseline. If any row lacks complete F=120 edge records or the common skeleton edge set, it is a data-integrity failure and H1 is not passed; do not impute or retry. Report row numerator/denominator, deviations, per-stratum mean and sample SD (`ddof=1` across the five seeds), and separate all-edge/path-edge values. H1 tests only the frozen A2c stored traces; A2f-3 descriptive values cannot change its status.

Timeout policy: no operation is launched; this is an offline deterministic scan of existing artifacts. Report missing/corrupt traces as failures and exclude none silently. Preserve all inputs by recording each config path, config SHA-256, source SHA-256 fields and result file SHA-256 in an inventory.

## Interpretation limits

The stored A2c paths are selected from finite iid pools and assembled by replacement, with up-frame groups bound by timeline path IDs; therefore empirical frame-to-frame toggles need not match an unconditioned iid edge process. The A2f-3 outputs use `patched-v3` per-edge Markov chains followed by exact S–R state projection, which can alter edge marginals and durations. Results describe saved artifacts, not a universal sampler property. One graph realization per family applies to these stored grids. Later stages retain the adopted `uk` timeline, instantaneous per-frame usable S–R uptime as the oracle (no waiting), and time-respecting reachability as descriptive only, labelled “allows store-carry-forward”. The MPC fail-closed change remains proposal-only, and `alpha/EM/` stays untouched.
