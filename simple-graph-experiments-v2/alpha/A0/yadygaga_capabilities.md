# Alpha A0 — YaDyGaGa capability audit and decision

**Audit date:** 2026-10-09  
**A0 status/verdict: STOP — seed-diversity gate failed; user review required before A1.**  
**Variants spent:** 0. **A1 status:** not started and not authorized.

## Decision summary

The clean YaDyGaGa source completed all 30 planned generator-only cases using the Alpha-authorized wrapper route. The N=162, 120-frame timing gate passed in all three repetitions (maximum 0.184 s, versus <600 s); N=92 path-life fidelity passed for every preregistered seed at 0.3/0.5/0.7. The stop-critical diversity gate **failed**: the five N=92, 120-frame, life-0.5 runs produced only one unique S–R connectivity bit timeline, with mean pairwise Hamming fraction 0.0 (required ≥5 unique and >0.10). Under the campaign’s A0 stop rule, stop for user review and do not start A1.

The authorized route used the preregistered clean YaDyGaGa HEAD snapshot at `/tmp/yadygaga-alpha-a0-clean` and the new A0-only wrapper under alpha/A0; the dirty YaDyGaGa checkout and modified G2DG-SPC.py were not imported or executed. The wrapper used for all generation workers had SHA-256 `eafb56abf7482f90aed77f56ea2a9e19fc198156c9fb02efc90dc3e631c6cbec`. The campaign explicitly directs that adaptations live in new Alpha wrappers (docs/Alpha campain.md, lines 11–15). A first full batch generated all 30 traces and per-trace records, but the post-run CSV aggregation raised a field-selection error. The wrapper was fixed in aggregation-only mode, then summaries were computed from the saved records without rerunning trace generation. All 30 output files passed independent size/hash verification.

## Source identity and reproducibility boundary

- Repository: YaDyGaGa, origin `https://github.com/Petitnuagedk/YaDyGaGa.git`.
- Package metadata: `yadygaga` version `0.0.5`, in `pyproject.toml`; no release tag/version pin was used for this audit.
- Package metadata: `yadygaga` version `0.0.5`, in pyproject.toml, line 3; no release tag/version pin was used for this audit.
- Repository HEAD: `51b01ac7faa78a494c3baedc560d658f384afe09`.
- The external checkout is not clean: `yadygaga/timelineBlockGenerator.py` and `yadygaga/toolbox.py` are modified. The J2 worktree’s G2DG-SPC.py is modified too. Do not conflate either working-tree state with the committed source.
- SHA-256 of the clean YaDyGaGa HEAD blobs:

| Source at YaDyGaGa HEAD | SHA-256 |
|---|---|
| yadygaga/frameGenerator.py | `76f5e62514a571359ac74718b80eab97d26d366dbe64179a0069d5e9ceeaed4d` |
| yadygaga/timelineBlockGenerator.py | `9b1601c9eba81528582f11b290dd35a5e95f18df560346287c4d32e6e9cbf9d7` |
| yadygaga/sourceGraphAugmenter.py | `5e5319ed0fd7b465cc83c7fbcb53405b4b2251c9eefb6c9b7ea17e802fab62c8` |
| yadygaga/dynaGraph.py | `e4427662bd3d61e1cfde87756a05b44a6102a331baab4f0a76d07060600a8be0` |
| yadygaga/toolbox.py | `d913a07feaa1591151314314b888deeba56e846e9037e6e4a0f0eda1fd704b5a` |

- The working-copy hashes differ for both dirty modules: timelineBlockGenerator.py `49506167cf764705e4e3fc7d3944d070dc2602c69b8ae250fcf3fc6e851591f5`; toolbox.py `a5b977aaff8aa132d3b7c53b6609863fb6393e94a03bee239a12399ce144e485`.
- Other A0-relevant source evidence is cited against the clean commit above. In that commit, frame generation samples each edge in the supplied graph independently using the global RNG and p_edge, partitions sampled graphs according to S–R reachability, and groups up-frames by shortest-path node sequence (yadygaga/frameGenerator.py, lines 20–67). The MPC counterpart accepts a list of pairs and a seed-local RNG, generates shared sampled frames, and returns per-pair path/reachability metadata (same file, lines 69–159).

## Capability findings and axis verdicts

The classifications below combine source inspection with the preregistered measurements where applicable. A failed seed-diversity gate makes the overall generator verdict not usable for Beta.

| Axis | Source/API finding | Verdict |
|---|---|---|
| Path life | SPC timeline API exposes path_life. Clean HEAD computes `round(frames * path_life)`, clamps the frame count to `[0, frames]`, and creates a Boolean timeline with that quota (yadygaga/timelineBlockGenerator.py, lines 12–52). The library’s own helper instead documents a ceil quota (yadygaga/toolbox.py, lines 26–42, 78–91). The constructed traces realized exact requested uptime at N=92/120 for all 15 preregistered seed/condition cases. | **Usable for path-life fidelity.** A0 empirical rule passed; note the toolbox ceil-vs-generator round discrepancy. |
| Stability | SPC API exposes stability and maps it to a requested number of up-blocks; the blocks are split/interleaved to form the timeline (yadygaga/timelineBlockGenerator.py, lines 109–119, 138–235). The helper defines stability as unchanged adjacency fraction, but the generator uses a heuristic block-count mapping rather than directly targeting that statistic (yadygaga/toolbox.py, lines 33–42). | **Partly usable.** Separate input, but the API’s empirical transition/stability fidelity was not measured and helper semantics are not the same construction rule. |
| Path persistency | `pathPersistency` is a distinct timeline-generator input; for successive up frames it probabilistically retains or changes an integer path ID (yadygaga/timelineBlockGenerator.py, lines 12–27, 246–269). In SPC frame generation the parameter is only range-asserted/accepted; it does not affect sampling (yadygaga/frameGenerator.py, lines 20–38). The assembly API maps persistent IDs to path groups (yadygaga/dynaGraph.py, lines 36–47, 78–108). The clean assembly class uses an unseeded `random.Random()` (line 49), so the timeline seed alone does not make final frame selection repeatable. | **Partly usable.** ID-level control exists and is separate from life/stability, but end-to-end realization and reproducibility were not measured. |
| Random-link fraction | `p_edge` independently samples each edge already present in the supplied limited/base graph (yadygaga/frameGenerator.py, lines 25–48). It is an edge-retention probability, not a facility for adding random non-skeleton links. | **Partly usable only as sampled-edge fraction.** Not demonstrated as a distinct random-link fraction control. |
| Random-link lifetime | No link-level lifetime/duration parameter is present in the SPC frame-generator signature or sampling loop (yadygaga/frameGenerator.py, lines 20–67). Persistence applies to path IDs in the separate timeline generator, not per-link lifetime (yadygaga/timelineBlockGenerator.py, lines 246–269). | **Not usable as a distinct control in the inspected SPC API.** No 2×2 diagnostic was run. |
| Number of constrained paths | SPC takes one source and one destination (yadygaga/frameGenerator.py, lines 20–28). The MPC sampler accepts an arbitrary list of pairs and reports per-pair paths (lines 69–90, 122–159); the MPC timeline accepts n_pairs (yadygaga/timelineBlockGenerator.py, lines 276–330), and the assembly class consumes joint status tuples (yadygaga/dynaGraph.py, lines 494–550). The example demonstrates two pairs (exemples/mpc.py, lines 20–43). No maximum is specified, and shared-node runtime behavior was not measured. | **Usable for multiple pairs at the API level.** Two pairs are demonstrated; there is no documented maximum, and shared-node runtime behavior remains unverified. |
| Seed diversity | Timeline generator calls global `random.seed(seed)` (yadygaga/timelineBlockGenerator.py, line 45); MPC frame generation uses `random.Random(seed)` (yadygaga/frameGenerator.py, line 92). SPC frame generation itself uses global RNG without seeding (lines 43–48), while clean SPC assembly initializes an unseeded local RNG (yadygaga/dynaGraph.py, line 49). | **Not usable under the frozen seed-diversity gate.** All five measured S–R bits were identical; uniqueness=1 and mean Hamming fraction=0.0. |
| Infeasibility / invalid inputs | SPC frame generation asserts `0 <= pathPersistency <= 1` but does not validate p_edge (yadygaga/frameGenerator.py, lines 20–48). Timeline generation clamps the up-count but does not validate path_life/stability (yadygaga/timelineBlockGenerator.py, lines 45–52, 109–119). SPC assembly substitutes empty graphs if an up/down pool is empty (yadygaga/dynaGraph.py, lines 86–108 and corresponding down-pool branch); therefore requested states may not be realized by the constructed graph if pools are missing. J2’s wrapper instead returns no result when either pool is empty (current G2DG-SPC.py, lines 90–92, 195–196). | **Partly characterized from source; failure behavior not tested at A0 scale.** |

### Path-life arithmetic and measured fidelity

The clean timeline source’s round-based requested count implies 36, 60, and 84 up states for 120 frames at path_life 0.3, 0.5, and 0.7 respectively. Every one of the 15 measured N=92 traces had nonempty up/down source pools and assembled S–R uptime exactly equal to the requested value (absolute error 0.0; all ≤0.05). This passes the preregistered fidelity criterion. The discrepancy with the toolbox helper’s ceil definition remains documented and was not silently reconciled.

## API, constraints, random links, outputs, and failure modes

- The documented SPC demo calls `SourceGraphAugmenter.augmentBaseGraph`, `FrameGenerator.generateSPCFrames`, `SPCTimelineBlockGenerator.generate_blocks`, and `SPCDynamicGraph.buildDynaGraph` (exemples/spc.py, lines 20–47). It is a demo with 500 sampled frames and a 40-frame output, not the specified A0 measurement interface. It also declares a pair A–F but calls the sampler for A–D (lines 31–37), so it is not an unambiguous validated harness.
- `augmentBaseGraph` accepts a group/list of source-destination pairs, computes baseline shortest-path lengths, shuffles candidate nonedges with a local seeded RNG, and greedily admits edges only if no group pair’s baseline distance decreases (yadygaga/sourceGraphAugmenter.py, lines 43–73, 75–120). It can augment the supplied base graph, but it does not specify random-edge fraction or edge lifetime. The inspected J2 SPC wrapper sets `limited = G` and comments out augmentation (current G2DG-SPC.py, lines 78–84 and 188–192).
- SPC’s frame sampler generates up to `trials` candidate graphs; it does not guarantee that both up and down pools are nonempty. Clean assembly uses an empty-graph fallback for absent pools (yadygaga/dynaGraph.py, lines 86–108 and 109 onward); J2 wrapper exits early instead (current G2DG-SPC.py, lines 90–92). No explicit infeasible-request exception or request-repair API is provided for this path.
- Toolbox export writes a node list, stacked per-frame adjacency matrices in frames.csv (blank-line delimited), and metadata (clean yadygaga/toolbox.py, lines 312–399). This output routine creates directories and may delete files under overwrite=True (lines 335–352); it was not invoked for A0.
- Current G2DG’s wrapper has a file-path interface used by the J2 pipeline: the runner loads `args.dg_script` and defaults it to `J2/G2DG-SPC.py` (run_pipeline-sweep.py, lines 251–261 and 643–652). Its stage 2 calls the wrapper; A0 did not call the runner or wrapper.

## Read-only G2DG-SPC comparison

- J2 HEAD: `ed1425c2cc3e62eafa7be0d9e821d5cca7a7e43b`.
- Current worktree G2DG-SPC.py SHA-256: `3231c9c6a8b4a25f3fbfd5d3eadfd0c785b45043fd90bfb3c39ba5e6f390a03b`.
- J2 HEAD version SHA-256: `7b9fae20971bec09cd72fba37f162f64e574e1e63aa290b52867cc4cca7eab67`.
- Diff summary: 90 changed lines; 56 insertions and 34 deletions. Diff was inspected read-only; this report does not reproduce or alter it.
- Semantic differences from HEAD:
  1. `test_pair_on_graph` and `build_dynamic_graph` now seed Python’s global RNG before SPC frame sampling (current G2DG-SPC.py, lines 81–84 and 190–192).
  2. A new `_assemble_spc_frames` uses a local `random.Random(seed)` and explicit path-ID-to-group mapping; normal and sweep generation use it instead of `SPCDynamicGraph.buildDynaGraph` (lines 144–170, 99–102, 203–205, and 284–334). That changes final frame-selection RNG and reproducibility semantics; clean YaDyGaGa’s own assembly uses an unseeded local RNG.
  3. `sweep_spc_generate` now samples its up/down frame pools once for all sweep modes; the pathPersistency sweep no longer resamples per value. Thus its previous pool-refresh behavior changes (lines 244–248, 269–300). The new function’s comments correctly say frame-sampler `pathPersistency` is compatibility-only; path-ID assignment is the timeline-level effect.
  4. The wrapper API still centers on one pair `(a,b)`; it is not the MPC multi-pair API. The sweep function handles path_life, stability, and pathPersistency but not random-link fraction/lifetime.
- Current source/hash and exact diff evidence was captured before this report; provenance/approval for the worktree modification remains unresolved. Do not import or execute this file for A0 until explicitly cleared.

## Measurements and A0 gate table

| Required item | Result |
|---|---|
| N=42, 92, 162 × 60/120 frames, seeds 42–44, three timing/RSS/output-hash repetitions | **Completed: 18/18 timing-cell traces.** Full raw per-trace records, output bytes and hashes: [measurements.csv](results/measurements.csv), with corresponding record and serialized trace JSON in results/. |
| N=92, life 0.3/0.5/0.7, seeds 42–46; S–R uptime and five-bitstream diversity | **Completed: 15/15 traces.** All requested S–R uptimes realized exactly; life-0.5 bitstream uniqueness=1/5, mean pairwise Hamming fraction=0.0. See [seed diversity](results/seed_diversity.json) and [path-life fidelity](results/path_life_fidelity.json). |
| N=92 random-link fraction/lifetime 2×2 diagnostic | **Not run.** Source inspection found no distinct random-link lifetime control; the API samples skeleton edges with p_edge and no additional experimental controls were invented. |
| N=162/120-frame each repetition <600 s | **PASS:** 0.1670, 0.1839, 0.1681 s; mean 0.1730 s, median 0.1681 s, maximum 0.1839 s. |
| N=92 path-life absolute error ≤0.05 for each seed and requested value | **PASS:** all 15 errors are 0.0. |
| At least five unique S–R bit strings and mean pairwise Hamming fraction >0.10 | **FAIL:** one unique timeline among five; mean pairwise Hamming fraction 0.0 (10 pair comparisons). This is the stop-critical failure. |
| Overall “usable for Beta” conditions (a)–(e) | **FAIL / not usable:** the seed-diversity requirement fails; random-link lifetime is also not an independent control. |

Run settings were 500 candidate frames, p_edge=0.5, stability=0.8, and pathPersistency=0.9; each deterministic Class-I geodesic used (m,n)=(ν,0), with the lexicographically first diameter pair as S–R. Python was 3.14.4. Timing covers candidate-frame sampling, timeline generation, and assembly; process RSS is absolute child-process high-water RSS (includes interpreter and imports), in KiB. Full output bytes/SHA-256, exact arguments, source hashes, S–R bit strings, pool counts, and realized features are in the per-trace records. The generator workers all completed; only the first attempt at CSV postprocessing failed, and the corrected aggregate-only pass consumed existing records without repeating any generation. Phase 7 evidence was not substituted.

| N | Frames | Wall mean / median / max (s) | Peak RSS mean / median / max (KiB) |
|---:|---:|---:|---:|
| 42 | 60 | 0.04215 / 0.03887 / 0.05085 | 94,084 / 94,032 / 94,200 |
| 42 | 120 | 0.04324 / 0.03861 / 0.05412 | 93,917 / 93,900 / 93,972 |
| 92 | 60 | 0.09191 / 0.09173 / 0.09356 | 104,995 / 105,012 / 105,016 |
| 92 | 120 | 0.10845 / 0.09523 / 0.13902 | 104,907 / 104,908 / 105,012 |
| 162 | 60 | 0.17113 / 0.17358 / 0.17397 | 117,164 / 117,140 / 117,304 |
| 162 | 120 | 0.17300 / 0.16811 / 0.18390 | 117,173 / 117,180 / 117,216 |

## Disposition and next action

**A0 verdict: not usable for Beta under the frozen overall rule; stop for user review.** Path-life fidelity and N=162 generation-time criteria passed, but the required N=92 seed diversity failed. Report the failure without changing thresholds or switching to the Edge-Markovian fallback. No A1, A4.0, Beta, protocol variant, or existing-generator modification is authorized by this report. A1 must not begin until the user reviews this A0 verdict and explicitly authorizes continuation.
