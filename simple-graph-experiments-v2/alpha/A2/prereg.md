# Alpha A2 preregistration — trace-feasibility and diversity audit

**Registered 2026-10-09 after A1 graph characterization and before any A2 timeline, frame-pool, or trace generation.** This document is preregistration only. **A2 execution is not authorized by the current task and will not be run.** Every new numerical decision below is labeled as **written after A0-R2 results** and the normalized-diversity criterion remains proposed, pending the user's approval.

## Scope, sources, and graph cells

- Static skeletons: exactly the N=92 graph from realization 1 of each A1 family, graph IDs `geodesic_N92_r1`, `rgg_N92_r1`, `ws_N92_r1`, `er_N92_r1`, `ba_N92_r1`. Their edge lists and hashes are in `../A1/results/graph_manifest.json`. Designated S–R pair is the A1 fixed structural rule: maximize equal-length shortest-path count; tie-break by larger hop distance then lexicographically smallest unordered pair. The A1 report records the five selected pairs and their path multiplicities. Do not change pairs after observing A2 outputs.
- Timeline implementation: A0-R2 isolated patched copy only, with selectable timeline source hash `c10fa53afaf4ce323835ed0ffd87de0322b6df7ccc63918c22736b409c13a8a4`, frame sampler hash `e84971f89cb966a574bf447ce8135c0c241b407be14e5066db2f82f3c2ec6b4b`, assembly hash `8e75cb59139516bfcc6ccfe672281575c4e8490fdf03d5d5bbcbef8a8b203c42`; isolated tree `32b243bc84b587f1782ead0d0ac56382a57425e5`, local commit `5a497f51815c85552fb0998b723460f16d0f50a0`. Do not edit upstream or the isolated source during A2.
- Cells: five graph families × life `{0.5,0.9}`; N=92; 120 frames; `mode="blocks"`; stability fixed at **0.9**; `pathPersistency=0.75`. One selected A1 graph per family, with its fixed A1 probe pair. Candidate timeline seeds are the ordered integers 42 through 241 inclusive, shared across cells for paired-seed comparison. The A2 seed decision is written after A0-R2; it is not derived from any A2 result.
- Each Boolean timeline candidate is generated from the patched timeline implementation. For the five selected distinct seeds in a cell only, form the random frame pool on that cell's skeleton using `FrameGenerator.generateSPCFrames(trials=3000, p_edge=0.5, pathPersistency=0.75, seed=timeline_seed+10000)`, then assemble 120 dynamic graphs using `SPCDynamicGraph.buildDynaGraph(..., seed=timeline_seed+20000)`. The pool is generated independently for each selected trace using the fixed seed mapping. Edge inclusion is the existing per-frame independent Bernoulli behavior; no generator edit or alternative is allowed.

## Infeasibility check and timeout

For F=120, A0-R2's exact feasibility condition is `K <= D+1`, where `U=round(F*life)`, `D=F-U`, and `K=round(1+(1-stability)*(U-1))`, clamped to `1..U`. At stability .9, life .5 gives U=60,D=60,K=7; life .9 gives U=108,D=12,K=12. Both satisfy the exact inequality. The registered F=120 infeasible-map cells are life=.7 at stability 0/.4 and life=.9 at stability 0/.4/.8; neither A2 cell is one of those. In particular life=.9/stability=.8 is excluded because it was infeasible in A0-R2. Do not add an infeasible parameter cell.

Every candidate timeline generation and every selected trace/frame-pool/assembly operation must run in a child process with a **60-second wall timeout per operation**. On timeout, terminate the child and mark the cell/run as failed due to noncompletion; no retries, extension of timeout, silent clamp, or substitute behavior. A timeout is a failure, not an omitted observation.

## Candidate selection and discarded seeds

For every family × life cell, generate and serialize all 200 candidate Boolean timelines for seeds 42–241 under the timeout rule. Scan in ascending seed order and retain the first five whose Boolean strings are pairwise distinct from those already retained. Record every seed and schedule hash, whether selected, and the discard reason (`duplicate_of:<earlier_seed>` or `after_fifth_distinct`). If fewer than five distinct schedules occur, that cell fails the diversity gate; do not search extra seeds. Evaluate all 200 candidates even after selecting five so duplicate-group diagnostics use the full preregistered pool.

## Diversity statistics and frozen comparison

For two 120-bit schedules x,y with requested uptime fraction `q=round(120*life)/120`, raw Hamming fraction is `H(x,y)=count(x_i != y_i)/120`, normalized diversity is `D(x,y)=H(x,y)/(2*min(q,1-q))`. Compute the following over the **five selected, pairwise-distinct** timelines unless noted otherwise:

1. Proposed post hoc rule, **written after A0-R2 results and not approved yet**: mean pairwise normalized D >= .30; at least five unique schedules; fraction of the ten unordered seed pairs with D < .10 is < .05.
2. On all 200 candidate timelines, largest identical-schedule group <= 10% of 200, i.e. <=20 candidates. Also report number of unique schedules across all 200.
3. Report the frozen original A0 comparison separately for each cell: at least five unique selected S–R timelines and mean pairwise **raw** Hamming fraction > .10. This is descriptive outside the original life=.5 A0 gate and does not change or extend that frozen gate.
4. Independent placement baseline: `D_independent=max(q,1-q)` (0.5 at life .5; 0.9 at life .9). Report observed mean D, baseline, their difference, and observed/baseline ratio per cell.

All new thresholds in items 1–2 are **written after A0-R2 results**. If mean normalized D is below .30, label that cell **“narrow by construction”** under this proposed criterion; do not relax the rule, expand the seed range, or change generator behavior. Stop at reporting and ask the user. A2 remains unauthorized regardless of an apparent pass.

## Fidelity, dynamic features, and time-respecting reachability

For each selected assembled 120-frame trace, log requested life, timeline up-count, measured S–R usable-frame fraction (1 iff a route exists in that frame), absolute uptime error, Boolean up-run lengths, mean and maximum up-run, number of Boolean state transitions, first down/outage frame (0-based; `NA` if absent), shortest-path hop count in each frame (`NA` when disconnected), static constrained-path hop count, and fraction of frames whose assembled S–R shortest path is strictly shorter than that static shortest-path constraint. The patched frame sampler samples only edges of the static skeleton, and the constraint baseline is the skeleton's shortest path, so this shorter-path fraction should be exactly zero; still record it, and treat any nonzero value as a provenance/measurement failure requiring a stop. Fidelity passes iff every selected trace has absolute measured uptime error <= .05. This .05 requirement is **written after A0-R2 results** and is unchanged from Alpha's frozen path-life fidelity criterion.

Time-respecting reachability is computed on a time-expanded graph: layer i contains every skeleton node at frame boundary i, for i=0..120; for each i=0..119 permit waiting `(v,i)->(v,i+1)` and permit `(u,i)->(v,i+1)` iff edge (u,v) is present in assembled frame i. For each start layer i=0..119, mark success iff R is reachable from S by layer 120; measured reachability is the successful-start fraction over the 120 start layers. Report requested timeline life minus this measured fraction per trace and cell. Do not call this instantaneous per-frame connectivity or packet delivery.

Across the five selected traces per cell, report sample SD (ddof=1) of each run-length-distribution bin (run lengths 1..120, each trace's normalized frequency per bin) and sample SD of first-outage frame over traces with a defined outage, together with its defined-trace count. If all traces lack an outage, report SD as `NA` and count 0. Report means and per-seed rows, not only aggregates.

## Required correction to a requested structural assertion

The request suggested stating that fixed life and fixed stability make both uptime and total transition count fixed by construction. Source inspection of the registered patched implementation does **not** support that assertion. Uptime and the requested up-run count K are fixed by construction; the allowed down-run category and boundary arrangement are also sampled, so total Boolean transitions can vary. At stability .9, the A2 cells have K=7 (life .5) and K=12 (life .9), and both admit more than one boundary/run arrangement. Therefore preregister only exact uptime quota and exact K as constructed quantities; record actual transition count per trace and its range, do not assume it is fixed or assert that replicates vary only placement. This corrects the requested statement without changing the generator or any frozen numeric threshold; user confirmation is requested before A2 execution.

## Stop / report rules

A2 is not run in this task. In a later explicitly authorized run, any timeout, empty required up/down candidate pool, fewer than five distinct schedules, failure of any approved diversity criterion, or fidelity error >.05 is reported without retries or threshold changes; stop and ask before proceeding to any later stage. No ns-3, Beta, or protocol variants are authorized. Protocol-variant cost for A2 is 0.
