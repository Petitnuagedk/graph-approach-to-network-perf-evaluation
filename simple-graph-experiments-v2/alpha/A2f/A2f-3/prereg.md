# A2f-3 preregistration — generator-only life/run-duration decoupling

Registered only after A2f-2 correction addendum 1 and PASS were logged. All new artifacts remain in `alpha/A2f/A2f-3/`. Do not modify A0/A0R/A0R2/A1/A2/A2d results or root `G2DG-SPC.py`. No protocol variants, ns-3, or A3. This is a generator-only descriptor study; it is not a routing-protocol performance experiment.

## Frozen common-feasible grid and Spearman feasibility check

Use F=120, lives `{.3,.5,.7,.9}`, U=`round(120*life)` = `{36,60,84,108}`. To give each life the same three **common feasible duration levels** without requesting unsupported integer quotas, first intersect the four finite mean-up supports. Under the A2f-1 K bounds, the smallest common feasible target is

`m_min = max_life(U/K_max) = 108/13 = 8.3076923077` frames.

For each life, the realized shortest-common cell is the smallest supported `U/K >= m_min`, giving K `{4,7,10,13}`. The largest common supported target not exceeding the registered 30-frame cap is

`m_max = min_life(max{U/K : K feasible and U/K <= 30}) = min(18,30,28,27) = 18` frames.

The geometric midpoint target is `m_mid=sqrt(m_min*m_max)=12.2285919688` frames. Select the supported value nearest this target by absolute log-ratio `abs(log((U/K)/m_mid))`; exact ties resolve to smaller K, giving K `{3,5,7,9}` and realized duration exactly 12 frames in all four lives. The longest-common cell chooses the largest supported `U/K <= m_max`, giving K `{2,4,5,6}`. Thus the three K rows by life are: life .3 `{4,3,2}`, .5 `{7,5,4}`, .7 `{10,7,5}`, .9 `{13,9,6}`. Each requested K is feasible. This common-support construction is preregistered to give a life-independent duration scale; the cap actually binds at 18 because the .3 cell cannot support 30.

Before trace generation, the correctly average-tie-ranked Spearman check on the 12 distinct `(life, U/K)` design cells is `rho=-0.0990867389`; the A2a comparison values below give `rho=1.0`. Seed/family replication does not add statistical units: primary correlation is computed once from the 12 unique UK design cells and once from the four unique A2a life cells, not by treating copied traces as independent. Gate: absolute UK Spearman `<=.30`; the frozen grid passes this design feasibility check before trace generation. Use a locally implemented average-rank routine with exact midranks for ties and Pearson correlation of those ranks; no SciPy dependency.

For the A2a comparator, use its A2c frozen stability rule with `stability=life`, `K=round(1+(1-stability)*(U-1))` (Python round-to-even), yielding K `{26,30,26,12}` and mean-up frames `{36/26,60/30,84/26,108/12}` = `{1.384615,2,3.230769,9}`. Its expected average-tie Spearman across four lives is exactly `+1.0`. This is a mathematical baseline, not a newly generated protocol or frame experiment.

## Trace design, sources, and seeds

Use the five A1 N=92 realization-1 graphs and A2c-frozen probes: geodesic_N92_r1 S/R=`0/31`; rgg_N92_r1=`14/47`; ws_N92_r1=`49/85`; er_N92_r1=`5/82`; ba_N92_r1=`5/72`. Retain all 92 nodes and treat skeleton edges as undirected. SHA-256 edge-list hashes: geodesic `bc0a8f616b04f3df961ee80dffa1a23132d9e11974f7b8e556f759eae7a24396`; rgg `ff6d4b830e9ebdd6ac9f8eff67e67c3af233c6fddf21c6e9379bdb41835137c4`; ws `0013ead659ca1be9be6c2f920bd917d4367f0c62062d8ff2fcbf46658cb26034`; er `443ea3ecb243798fb3a6fb97f71a83fc93b8606638d17e7882cd827fafb5ce2b`; ba `a6a31682b1c8b1c90d0b7a8d46213f0eaa95fb994ec45eaac720c1800d5e1328`.

Use the five A2b `greedy5` seeds per life, same five seeds across all families: life .3 `{42,63,178,107,56}`; .5 `{42,98,90,126,236}`; .7 `{42,228,199,235,44}`; .9 `{42,44,58,112,191}`. Each base seed determines timeline seed=`seed`, frame seed=`seed+10000`, assembly seed=`seed+20000`; record all. One trace for every family × life × three duration levels × five selected seeds = **300 trace operations**. Use pathPersistency=.75 and p_edge/pi=.5 throughout. No post-result seed substitution.

Use only the isolated A2d item1-derived A2f overlay for timeline behavior `uk`, with A2d item1 frame and assembler modules read-only. Freeze donor hashes from A2d item1: timeline `c10fa53afaf4ce323835ed0ffd87de0322b6df7ccc63918c22736b409c13a8a4`, frame generator `346ee8bc8399fbe1fa010927082a34c9156f56283512ecafe00d69d573a1b6bf`, assembler hash to be captured in the pre-run config and gate. Use frame behavior `patched-v3` with the fixed schedule passed as `timeline`, pi=.5, and the cell's realized supported mean-up duration; this emits connected up frames and disconnected down frames, each a subgraph of the A1 skeleton. Assemble with `SPCDynamicGraph.buildDynaGraph` and the registered stage seed offsets. This mode is non-upstream and descriptive only.

Every operation gets a config written before generation containing prereg hash, family/graph/probe/hash, F/life/U/K/requested and realized mean-up target, target class, timeline/pool/assembly seeds, persistency, frame behavior/p_edge/mean duration, source hashes, Python/NetworkX versions, and timeout. Persist schedule bits/path IDs, frame/pool status/counts, each assembled frame's edge list, connectedness/hops/canonical route, per-frame metrics, operation status, and per-trace metrics. Store one per-seed row; do not report aggregates alone. Sample SD uses `ddof=1` where at least two observations exist.

## Timeout and numeric gates

Each trace runs in a separate child process with 60-second wall timeout. A timeout or exception marks that operation failed and is not retried, replaced, clamped, or given a longer timeout. Continue independent registered cells only so missingness remains auditable. A2f-3 is operational PASS only if all 300 operations complete under timeout and all numeric gates below pass.

1. **Exact quota:** every trace realizes exact U and K, and the stated mean-up duration `U/K`; Boolean transitions and observed up-run list must reconcile exactly with the bit string. 300/300.
2. **Instantaneous S–R fidelity:** for every frame record `is_connected(S,R)`; it must equal that frame's timeline bit exactly. Report per-trace connected-frame fraction and absolute error from requested life. Gate: zero mask disagreements and absolute fraction error <=.05 in all traces.
3. **Shortcuts/provenance:** a shortcut is a frame route with fewer hops than the A1 static skeleton shortest-path distance. Since assembled frames must be skeleton-edge subsets, shortcut fraction must be exactly zero in all 300 traces; every sampled edge must belong to the A1 skeleton. Any shortcut or out-of-skeleton edge is a hard provenance failure.
4. **Duration decoupling:** calculate average-tie Spearman on the 12 distinct UK grid centers as above; require `abs(rho)<=.30`. Report the A2a comparator Spearman on four unique A2a means (expected +1.0). Also publish all per-seed requested/realized values and life-level grouped values. Do not claim inferential independence from seed/family replications.
5. **Route/hop summaries:** record canonical lexicographically smallest minimum-hop route per frame (None if disconnected), NetworkX's insertion-order route separately, static skeleton hop count, and per-frame hop count (`NA` when disconnected). Route diversity is descriptive, not a gate in A2f-3.
6. **Temporal reachability:** compute time-respecting reachability using the A2 predecessor rule: layers 0..120 include all 92 nodes; at every frame allow waiting at every node and traversal over an assembled frame edge; from each start layer i, success means R is reachable from S by layer 120. Report success fraction and `life - reachability` as **store-carry-forward descriptive reachability**, not an OLSR/AODV/DSDV oracle and not a protocol performance metric. No pass threshold.

The six carry-forward limitations must appear in result tables/report: life and mean up-run are confounded under A2a stability; timeline diversity is family-independent by construction; generator is patched non-upstream; A2b gate is non-binding by construction due to greedy max-min selection; Level 2 route diversity is tie-break-sensitive; time-respecting reachability allows waiting and is not a protocol oracle. A2f-1's support boundary remains binding: shared durations are limited to the intersection of finite supports, and 30 frames is only an upper cap, not an attained common duration. No protocols, ns-3, or A3.
