# A2d item 3 preregistration — end-to-end seed reproducibility

Registered after A2d item 2 correction v1 result was entered in `alpha/gates.md`, before item 3 runner code or any reproducibility run. Generator-only, no ns-3, no protocol variants. The prior binding question is whether a single recorded seed mapping controls timeline generation, SPC frame-pool sampling, and assembly so that independent reruns are bit-identical, specifically avoiding the unseeded RNG in the archived clean legacy SPC assembler.

## Fixed pipeline and repetitions

Use the isolated A2d item 1 source copy and A1 N=92 ER realization 1 (`er_N92_r1`, graph edge-list hash recorded in each config). One fixed pair `(5,82)`. For each base seed `{11,29,47,71,97}`, run two independent child processes with the identical full configuration, giving 10 operations and five paired repeat comparisons.

Each run generates a 120-frame SPC timeline using `SPCTimelineBlockGenerator(frames=120, path_life=.5, stability=.5, seed=base_seed, mode="blocks", pathPersistency=.75, behavior="patched")`; samples `trials=3000` legacy-compatible SPC candidate frames with `p_edge=.5`, `seed=base_seed+10000`, `behavior="legacy"`; and assembles with active isolated `SPCDynamicGraph.buildDynaGraph(..., seed=base_seed+20000)`. Record all three stage seeds explicitly. Do not use `dynaGraph.legacy.py`'s no-argument `random.Random()` assembler in the seeded pipeline; that archived method has no seed parameter and is retained solely as a source-audit reference, not a candidate execution arm. No implementation/source edits are allowed for this item; this is an audit of the seeded APIs in the isolated copy.

Write a full config before each child, with graph and source SHA-256s, all parameters/seeds, Python/NetworkX versions, run/repetition IDs, and this preregistration hash. Each operation is a fresh process with a 60-second wall timeout. No retry or replacement on timeout/error. Persist timeline/path IDs, sorted frame-pool edge fingerprints by group, assembled frame edge fingerprints, per-frame S–R status, and output hashes.

## Numeric gates

1. **Completion:** 10/10 operations complete under 60 seconds, no retry.
2. **Stage determinism:** for every base seed, repeat 1 and repeat 2 have exactly equal byte-level canonical JSON hashes independently for timeline+path IDs, entire ordered frame pool, and assembled dynamic frames. Required: 5/5 pairwise matches at each of the three pipeline stages (15/15 comparisons).
3. **Assembly target fidelity:** in each operation, assembled S–R reachability mask equals its requested 120-bit timeline exactly (10/10); no empty required up/down pool; all assembled edges are a subset of the fixed ER skeleton (10/10).
4. Report stage runtimes and per-operation total plus mean and sample SD (`ddof=1`) by stage across the ten runs. Runtime does not substitute for any identity gate.

This establishes reproducibility only for this isolated source/version, fixed graph/pair, parameters, interpreter, and seed mapping. Do not generalize across Python/NetworkX versions or claim the legacy unseeded assembler is reproducible. Preserve A2d item 2 initial failure and correction v1 outcomes; item 3 does not change their conclusions. Log this result before registering item 4 or A2e. Item 4 remains proposal-only pending explicit approval. 0 protocol variants.
