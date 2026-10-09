# S–R timeline seed redesign — read-only resolution

## Finding

The Phase 5 S–R bit timelines are identical because the per-seed RNG does not control the timeline construction for the tested cells; the block schedule is quota-derived and deterministic. This is **not** evidence that the configured realization seeds were all the same.

- The pipeline advances the DG seed for each graph realization (`seed = base_seed + graph_epoch - 1`) at [run_pipeline-sweep.py](../../run_pipeline-sweep.py#L397-L402). Phase 5 configs confirm graph_0001 uses DG seed 42 and graph_0005 uses 46.
- The sweep passes that seed into `sweep_spc_generate()` and calls `random.seed(seed)` before `FrameGenerator.generateSPCFrames()` at [G2DG-SPC.py](../../G2DG-SPC.py#L269-L278). The frame-pool generator then uses global `random.random()` per candidate edge when sampling its 1,000 graph samples. Thus the seed affects which concrete up/down graphs and path pools are available.
- The same seed is passed into each `SPCTimelineBlockGenerator` call for every sweep value at [G2DG-SPC.py](../../G2DG-SPC.py#L284-L293), [G2DG-SPC.py](../../G2DG-SPC.py#L306-L316), and [G2DG-SPC.py](../../G2DG-SPC.py#L323-L336). The imported timeline generator computes `up_count = round(frames × path_life)`, derives `up_blocks` deterministically from stability, deterministically splits counts, and interleaves them. For the Phase 5 block-mode cells, those steps leave no random choice affecting the Boolean schedule. Its RNG is used for special one-block placement and then for `path_ids`; those `path_ids` control route identity, not S–R connected/disconnected state.
- Path-persistency sweep explicitly documents that persistency affects only path IDs, not sampled frames or the connectivity schedule, at [G2DG-SPC.py](../../G2DG-SPC.py#L269-L293).
- Frame assembly uses another local RNG seeded by the same realization seed, selecting concrete network graphs within the already-generated Boolean up/down schedule. This can change non-S–R edges, but cannot change whether the S–R path is up: up-pool elements have S–R connectivity by construction; down-pool elements do not.

The measured audit agrees: all Phase 5 topology × sweep-cell groups have 1 distinct S–R timeline among 5 configured seeds and mean pairwise Hamming distance 0; same-seed traces are also exactly equal across the three topologies. See the Phase 6C [cell diversity results](../phase6/6C/cell_summary.csv) and [cross-topology equality results](../phase6/6C/cross_topology_seed_equality.csv). The missing variation is in the Boolean timeline RNG path, rather than in the recorded seed increment.

## Recommended v2 design (proposal only; no generator edits made)

Use separate, deterministic random streams with domain-separated seeds derived from a stable hash or `numpy.random.SeedSequence`, never Python's process-randomized `hash()` and never global `random.seed()` state:

1. `timeline_rng`: keyed by master seed, topology ID, unique parameter-tuple ID, realization ID, and a fixed stream tag. It must drive placement and run-composition randomization of the S–R up/down sequence.
2. `graph_pool_rng`: independently samples candidate up/down graph frames and path groups. Changing this stream must not affect `timeline_rng` output.
3. `path_identity_rng`: assigns route/path IDs only on consecutive connected frames according to `pathPersistency`; it must not affect the Boolean timeline or its run statistics.
4. `replay_rng`: remains separate in ns-3 and must not be reused as a DG seed stream.

For a trace of $F$ frames and requested path life $p$, set the up quota once as $U = \operatorname{round}(Fp)$ and the down quota as $D=F-U$. The schedule generator should construct seeded, randomized run placements subject to the exact quotas, rather than deterministically splitting and interleaving blocks. Store the master/derived seeds, stream version, and realized S–R bit-string hash in each trace config.

To remove the current stability/mean-up-run confounding, add an explicit `mean_up_run_frames` (or equivalent up-run-count) design variable. For the proposed 60-frame acceptance design, use target mean 5 frames and choose $K=\lceil U/5\rceil$; more generally derive/validate integer $K$ from the explicit target and report the realized $U/K$. `stability` in v2 should control the dispersion/regularity of positive up-run lengths **conditional on fixed $U$ and $K$**, not change $K$. A precise mapping is: compute the attainable coefficient-of-variation (CV) range over positive integer compositions of $U$ into $K$ runs, then linearly map `stability=1` to the minimum attainable CV and `stability=0` to the maximum attainable CV, selecting a seeded composition closest to the target. Changing stability must leave uptime, transition count, and mean up-run unchanged. If a requested dispersion cannot be achieved for that finite composition, reject the cell rather than silently changing another feature. `pathPersistency` controls only route identity retention within the up intervals and must leave S–R uptime, up-run lengths, and transition count unchanged. This changes v2 parameter semantics, so retain the legacy generator path and version the new semantics explicitly; do not silently repurpose old results.

Randomization must also include the positions of the up/down blocks, not just permute concrete graph instances. Boundary policy (whether traces may start/end up) must be fixed before coding and recorded, because it changes the feasible transition/run-count set.

## Proposed acceptance thresholds

For each of the **39 unique Phase 5 parameter tuples** across line, two-lines, and ladder, generate five diagnostic traces using five distinct realization IDs; repeated center-point materializations are not counted as separate cells. These are generator-only tests and consume **0 protocol variants**. Before any later simulation plan is authorized, require all of:

- At least **5 distinct** S–R timelines among the 5 requested realization IDs.
- Mean pairwise Hamming distance divided by frame count is **at least 0.10** (at 60 frames, at least 6 differing frame positions on average across the 10 pairs).
- Each trace’s measured S–R up-frame count differs from `round(F × requested_path_life)` by **0 frames**; equivalently, absolute uptime error is at most `1/F` and the quota is exact.
- Holding all other settings fixed at 60 frames and path life 0.5, the mean up-run CV across five traces must be nonincreasing as stability increases over the five Phase 5 stability values; adjacent settings may differ by at most 0.05 in the wrong direction, and the mean CV at stability 0.0 must exceed that at 0.8 by at least 0.10. At every stability value, uptime, transition count, and mean up-run must be identical across the compared realizations. Changing only `pathPersistency` changes route-identity retention but leaves the S–R bit-string hash, uptime, up-run lengths, and transition count exactly unchanged; if an up trace contains at least 20 adjacent-up frame pairs, observed identity-retention fraction must be within 0.15 of requested persistency, otherwise report numerator and denominator without using it as a gate.
- Regenerating a trace with the same full seed tuple yields byte-identical serialized frames and metadata; changing realization ID changes the timeline for every nondegenerate tested cell.

For frames where exact five-way diversity or Hamming distance is mathematically infeasible under the approved boundary/run-count constraints, the generator must report that infeasibility before simulation. Such a cell is a failed acceptance test, not a reason to reduce thresholds after observing results.

## Decision and stage boundary

The root cause and recommended redesign are resolved at the analysis/proposal level. This document makes **no generator change**, and authorizes **no 7C protocol variants**. Subsequent work completed the 7B implementation and B2 legacy regression, but original B1's aggregate-PDR/usable-uptime criterion failed; therefore 7B did not pass as a whole and gated order still blocks 7C. The 7D offline generator acceptance audit has since passed, but does not cure B1 or authorize 7C. Any future 7C plan still requires separate approval and validated diverse traces.
