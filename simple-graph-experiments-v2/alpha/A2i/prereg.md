# A2i preregistration — disjoint multi-pair timeline-fidelity diagnosis

Registered before any A2i measurement or source-copy execution. Generator-only; no ns-3, graph-run, protocol variant, or protected-tree execution. All new artifacts are confined to `alpha/A2i/`; the A0R2 source is copied read-only into `alpha/A2i/src/` before any patch.

## Frozen inputs and cases

Use the exact A2d item-2 correction-v1 design: A1 ER N=92 realization 1 (`er_N92_r1`), edge list and hash recorded from the item-2 configuration; no new skeleton or pair selection. Disjoint pairs are the prefix sets of `[(0,1),(2,3),(4,5),(6,7),(8,9),(10,11),(12,13),(14,15)]` at m=2,4,8. The exact seeds are `{11,29,47}`. The timeline is 120 frames, `path_life=.5`, stability `.5`, synchronous mode, `pathPersistency=.75`; assembly uses `no_double=True`, `allow_hamming_fallback=True`, `force=True`, and assembly seed `seed+20000`; pool seed is `seed+10000`.

Test `p_edge` values `{0.3,0.5,0.7}` and candidate budgets `{3000,30000,300000}`. The full frozen grid is 3 pair counts × 3 seeds × 3 probabilities × 3 budgets = 81 child operations. Each operation has an individual 60-second wall timeout, no retry, no replacement, and timeout/failure is recorded.

## Step 1 metric checks

Before hypothesis measurements, run known-answer tests using a hand-built two-disjoint-pair skeleton: (a) a prescribed four-state sequence with known per-pair uptimes and (b) pair A always up and pair B always down. Fidelity passes only when every pair's measured uptime error is <= .05; per-pair uptime is up frames divided by frame count. ID-labeled timeline entries must be converted to status by `value is not None`, and tuple counts must be computed after this conversion. Any check failure stops A2i before generator measurements.

## Numeric classifications and decisions

A joint state is **scarce** when its pool count is `< 10` frames at a given operation; zero is explicitly absent. A configuration is **supply-ready** when every joint state requested by its timeline has at least 10 candidate frames. Fidelity success requires every pair's assembled uptime to be within the A2d item-2 tolerance of `.05`, with successful completion, registered endpoints, and all assembled edges in the N=92 skeleton. A fix is accepted only if disjoint fidelity improves on the frozen 81-cell grid relative to the isolated baseline at the same cells and shared-source fidelity on the exact A2d correction-v1 grid is not reduced (shared-source is a preservation regression check, not pooled with disjoint results).

H1 (horizon/budget) is supported if fidelity increases with budget in the same p/seed/m cell(s), and at least one previously failing disjoint operation becomes successful at a larger budget while its requested states become supply-ready; it is not supported if fidelity stays flat despite supply-ready pools. H2 (nonexistence/rarity) is supported as persistent absence evidence when a requested state has zero frames at the largest budget for at least 2 of 3 seeds at a p/m cell; because this is finite random sampling, the report must call it evidence of model-level scarcity/absence, not mathematical impossibility. H3 (assembly) is supported if requested and realized status sequences diverge while all requested states are supply-ready (>=10 each), or if a frame is replaced by an empty graph/substitution despite an available exact candidate. The first matching classification is not exclusive: multiple hypotheses may be supported; none may be supported; an operation timeout is undetermined for that operation.

A candidate fix is attempted only if H1 or H3 is supported. H1 fix: smallest isolated change is an adaptive candidate budget up to the preregistered 300000 cap with explicit failure at cap when an exact requested state remains unavailable; no silent fallback relaxation. H3 fix: smallest mapping/substitution correction with explicit failure instead of empty-graph or wrong-status substitution. H2-only results receive no workaround. Report all classifications with evidence and do not generalize beyond this grid.

## Hashing and reporting

Record SHA-256 for every copied/modified source file used, every input, every output table/report, the preregistration, and the unified diff/dry-run artifacts if a fix is made. Use sample standard deviations with `ddof=1` wherever SD is reported. Stop after writing `result.md` and appending the dated gate entry.
