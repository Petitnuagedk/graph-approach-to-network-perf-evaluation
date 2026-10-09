# Phase 7A integrity audit

## Scope and preregistered gates

This is a read-only audit; no simulation was run and no Phase 0–6 file was modified. The criteria are those in [prereg.md](prereg.md): resolve topology for all 15 6A run configs; exact SHA-256 matching for traces; per-row PDR difference at most `1e-12`; count unique Phase 5 tuples and materializations; and inspect all six known divergent routes for exact sequence equality. Per preregistration, no overall pass/fail is assigned to 7A. Phase 6’s 6A manifest identifies 15 graph-run invocations and 45 protocol variants.

## Findings

### 1. 6A topology and baseline suitability

The 6A manifest records **line topology only**. Independently resolving the `frames_csv` source path in every per-run replay config gives 15/15 paths under `phase5/line/` (zero unresolved or mismatched); topology is not a top-level field in those replay configs. The Phase 5 baseline sweeps include line, two-lines, and ladder, but **line is the exact 6A topology match**. The 6A per-graph AODV/static PDR rows are identical to the first epoch of the matching Phase 5 line cell for all five graph realizations and all three settings checked:

| Matching DG setting | AODV equal / 5 | Static equal / 5 |
|---|---:|---:|
| stability 0.0 (fixed path life 0.5, persistency 0.75) | 5/5 | 5/5 |
| path life 0.7 (fixed stability 0.8, persistency 0.75) | 5/5 | 5/5 |
| path life 0.9 (fixed stability 0.8, persistency 0.75) | 5/5 | 5/5 |

This demonstrates result-row consistency with one Phase 5 replay epoch, not an independent replication. It does not make 6A a multi-topology experiment. Therefore, **any 6A claim about topology variation or topology-robust behavior is invalid and must be withdrawn**. It is permissible to retain only the explicitly line-topology results as a descriptive baseline, subject to the other Phase 6 limitations and separate Phase 7 repair gates.

For the requested cross-topology comparison, the values below are arithmetic means across five graph IDs. Phase 6A summarizes one replay epoch per graph; Phase 5 values average five replay epochs within each graph before averaging the five realization means, so these are descriptive checks, not identical estimands.

| Condition | Source | Topology | AODV PDR mean | Static PDR mean |
|---|---|---|---:|---:|
| stability 0.0 | 6A | line | 0.90722240 | 0.36777780 |
| stability 0.0 | Phase 5 | line | 0.90877784 | 0.36766668 |
| stability 0.0 | Phase 5 | two-lines | 0.80677784 | 0.36766676 |
| stability 0.0 | Phase 5 | ladder | 0.49677780 | 0.36811108 |
| path life 0.7 | 6A | line | 0.93499980 | 0.66111100 |
| path life 0.7 | Phase 5 | line | 0.93266652 | 0.66111100 |
| path life 0.7 | Phase 5 | two-lines | 0.87266668 | 0.65055560 |
| path life 0.7 | Phase 5 | ladder | 0.56911120 | 0.63311096 |
| path life 0.9 | 6A | line | 0.98333300 | 0.86944400 |
| path life 0.9 | Phase 5 | line | 0.98199972 | 0.86944400 |
| path life 0.9 | Phase 5 | two-lines | 0.94022224 | 0.84777780 |
| path life 0.9 | Phase 5 | ladder | 0.70388876 | 0.82911124 |

The matching Phase 5 line conditions are consistent with 6A’s line-only provenance, while the two-lines/ladder outcomes differ. Those other topologies contextualize the baseline but cannot turn 6A into a topology comparison.

For the analogous Phase 4 / Phase 5 ladder path-life 0.9 comparison, the five 60-frame ladder trace files are byte-identical. Their SHA-256 hashes, graph_0001 through graph_0005, are respectively:

| Realization | SHA-256 |
|---|---|
| graph_0001 | `ef869d757857c33cf78d43844fa7581fddb2641410c5b10f77aff5125e9d24fe` |
| graph_0002 | `fc87f987a26863466a13f3806a9b4918caf675cb200ee2309b45daf4c0a89d36` |
| graph_0003 | `1e2c5bff4b126d648474ad0184db3f6f201a533be3cb95a3caa8bb94bf241ab9` |
| graph_0004 | `e4e9c33824d9eef00efb6f161782a21013c972eaa5c4fcca9b4a09bb78b3c5fd` |
| graph_0005 | `d20c6bad6fe32b769d2e9c8719cb7f58355945261777286fc06af0e362d85af9` |

All 75 paired protocol × realization × epoch PDRs match exactly (5 realizations × 5 epochs × 3 variants), satisfying the preregistered maximum difference of `1e-12` with observed maximum difference 0. The previously observed mismatch between the Phase 4 root summary and Phase 5 aggregate is a **summary-level comparison error**: Phase 4 root PDRs summarize only epoch 0001, whereas Phase 5 aggregates the arithmetic mean of five epochs within each graph realization and then summarizes the five realization means. For example, ladder graph_0001 AODV epoch 0001 is 0.708333 in both; graph_0001’s five-epoch AODV mean is 0.812222 in both. Across the five realization means, Phase 5’s AODV grand mean is 0.70388876; the Phase 4 root value .708333 is not that estimand. Static PDR is mostly invariant by realization and epoch, but graph_0005 has minor epoch-to-epoch values (0.836111/0.838889), also consistent across both roots. No replay discrepancy is indicated.

### 2. Phase 5 cell materialization and tuple duplication

The three sweep families for each topology materialize 15 cases. Their parameter tuples are `{path_life, stability, pathPersistency}` with fixed non-swept controls `(0.5, 0.8, 0.75)`. The center tuple `(0.5, 0.8, 0.75)` occurs once in each sweep family; the other 12 tuples are distinct. This means the preregistered expectation of the center tuple **exactly once per topology was not met**: it was materialized three times. The unique-tuple count below is the corrected value for later planning.

| Count | Per topology | Three topologies |
|---|---:|---:|
| Materialized cells | 15 | 45 |
| Unique parameter tuples | 13 | 39 |
| Repeated materializations of center tuple | 3 (2 redundant copies) | 9 (6 redundant copies) |

The shared center tuple is repeated as separate pipeline materializations and is not an independent generator condition. This is a design accounting note, not a correction to reported observations.

### 3. Generator-route versus serialized-trace oracle

The 6D seed-42 reproduction found **zero edge-state mismatches** over 60 frames and zero differing edge cells. However, generator-order NetworkX traversal and the serialized integer-label traversal choose different equal-length shortest routes in **6/60 frames**. Retention is 0.851064 in the generator graph and 0.744681 in the serialized-label oracle; consecutive-route changes are 7 versus 12. The saved route-difference rows show frames 40, 41, 46, 53, 55, and 56.

The behavior is explained by traversal order, not an edge-export defect. [G2DG-SPC.py](../../../G2DG-SPC.py) iterates graph nodes in graph insertion order while assembling/exporting; the trace serialization orders node labels. The external ns-3 `scratch/graph-run.cc` static-route `ShortestPath` constructs adjacency in serialized integer-index order and BFS keeps the first parent at an equal distance; [oracle_metrics.py](../../../oracle_metrics.py#L10-L31) likewise scans matrix neighbors in ascending label-index order. Inspection of all six preregistered divergent frames confirms the route sequences differ exactly as recorded in [route_choice_diff.csv](../../phase6/6D/route_choice_diff.csv), so the preregistered exact sequence equality criterion is **not met**. The static route and offline serialized oracle use the same deterministic tie-break policy; DG generator in-memory route may choose a different equally short path. Since the edge trace is identical, **claims that route-choice disagreement proves edge corruption are invalid**. Claims comparing generator-order route identity directly with serialized-oracle route identity must also be withdrawn or explicitly labeled as tie-break-sensitive. The Phase 6D audit quantified the impact: six route-choice frames, no edge differences.

### 4. Phase 3–5 conclusions to void or re-read

- **Phase 3:** its three frame-rate points remain observations for the one exact trace used. Any conclusion that extrapolates those observations to a population of independent connectivity timelines is void; the design had one realization.
- **Phase 4:** the dedicated 7A comparison establishes that its 1-fps ladder traces and Phase 5 ladder path-life 0.9 traces are byte-identical by graph ID and all 75 paired replay rows match, so those are repeated materializations, not an independent validation. Re-read any claim that treats those duplicated runs as independent validation. Phase 4 cross-realization timeline diversity was not separately audited here, so no stronger claim about its five realizations is made.
- **Phase 5:** per-cell CIs and SDs computed across five graph IDs do not quantify variation across independent S–R timelines where all five timelines are identical; statements about generality across dynamic-connectivity realizations are void. The center tuple was executed three times per topology, not once; do not count these as separate parameter conditions. The topology-specific raw observations remain descriptive only.
- **Across Phases 3–5:** interpolation with a 125 dB down value makes the modeled channel usable between binary frame states; binary uptime is not the channel’s effective usable uptime. Consequently, any interpretation of PDR against binary uptime or of frame-boundary timing under interpolation must be recalculated under the no-interpolation v2 channel. Static-route data are a measured routing reference only; they are not a guaranteed-performance bound and should not be used to rescale other protocol PDR values.

These invalidations affect conclusions and uncertainty, not the stored historical CSVs. The old artifacts remain untouched and must not be silently rewritten.

## 7A criteria results (informational; no overall pass/fail)

| Preregistered criterion | Observed result | Basis |
|---|---|---|
| Resolve 6A topology for all configs | 15/15 resolve to line; 0 unresolved | Each config's `frames_csv` is under `phase5/line/`; corroborated by manifest. |
| Compare Phase 4/5 ladder trace and replay results | 5/5 trace hashes match; 75/75 PDR differences are 0, max `0 ≤ 1e-12` | Root-summary discrepancy is aggregation level, not data divergence. |
| Count Phase 5 tuples/materializations | 45 materializations; 39 unique tuples; center tuple 3 times/topology | Preregistration requested center once/topology; actual materialization count exceeds that by 2/topology. |
| Inspect six route differences | 6/6 sequences differ; 0/60 edge mismatches | Exact route-sequence equality criterion is not met; tie-break explanation is supported. |

**Disposition:** 7A read-only audit complete. Phase 6 topology-variation conclusions are void. Preserve the 6A line-only rows only as descriptive, non-generalizable baseline observations; do not use them as evidence across topologies. Phase 4/5 repeated ladder PDRs are consistent at the preregistered threshold. Retain the Phase 6D edge-integrity conclusion, while documenting the tie-break qualification above. Phase 5's center tuple was duplicated contrary to the once-per-topology preregistration target and must be accounted for in later designs. This stage authorizes drafting the next preregistration only; it does not authorize a simulation or campaign.