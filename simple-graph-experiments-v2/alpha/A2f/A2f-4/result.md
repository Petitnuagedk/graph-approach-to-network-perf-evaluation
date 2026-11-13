# A2f-4 result — offline MPC multi-pair diagnosis

**Disposition: registered diagnosis and sweep completed; overall classification mixed/inconclusive.** The 18-cell correction-v1 audit and all 45 sweep operations were performed within the A2f-4 isolated scope. No upstream/protected source was changed, no ns-3 or protocol variants were used, no proposed fix was implemented, and A3 is not authorized.

## Preregistration correction and audit validity

The base preregistration and its amendment are [prereg.md](prereg.md), SHA-256 `931253195e235a56bfb2c9adcfa6c8ac60f6598e0d919cf4df7e5b82b5f4ab65`, and [prereg_addendum_1.md](prereg_addendum_1.md), SHA-256 `874117c922abcd4d42c6d0568a9fd5bfb8a27667d2696f9a3407dd370df6fa5a`. Addendum 1 was registered before accepting cause labels or starting the sweep. A preliminary read-only census had mistakenly compared MPC requested up-run counts to A2a's exact K=30; it showed 2–3 up-runs. Source review established that the legacy MPC generator uses a different exponential-run process, adjusts to exact U, and has no registered exact K target. The preliminary files [audit_18_cells.csv](audit_18_cells.csv) and [audit_18_cells.json](audit_18_cells.json) are retained as exploratory and superseded for quota/cause interpretation. The authoritative output is [audit_18_cells_v2.csv](audit_18_cells_v2.csv) and [audit_18_cells_v2.json](audit_18_cells_v2.json): all 18 cells have 120 frames and exactly 60 requested up-frames per pair; MPC run counts (2 or 3) are descriptive, not failures.

The authoritative first-match cause counts are: 6 `requested_joint_state_absent`, 3 `requested_pool_supply_below_demand`, and 9 `no_observed_fidelity_failure`. None had an invalid U quota. All 9 no-failure cells are the shared-source cells, whose 42/42 pairs pass. Disjoint cells have 3/42 pair-level passes overall (m=2: 1/6, m=4: 2/12, m=8: 0/24), agreeing with the correction-v1 result. These ordered labels are diagnostic summaries, not proof of causation.

| Arrangement / m | Cells classified | Pool cause | Observable selected-status mismatches | Pair-fidelity result |
|---|---:|---|---:|---:|
| disjoint / 2 | 3 | 3 under-supplied (requested `00`: 2–3 pool frames vs demand 60); no requested state absent | 57, 58, 57 frames | 1/6 pass |
| disjoint / 4 | 3 | all 3 missing requested `0000` (pool count zero, demand 60) | 60 per cell | 2/12 pass |
| disjoint / 8 | 3 | all 3 missing requested `00000000` (pool count zero, demand 60) | 60 per cell | 0/24 pass |
| shared-source / 2, 4, 8 | 9 | no requested state absent or under demand | 0 per cell | 42/42 pass |

**Limitations for this audit table:** life and mean up-run remain confounded under A2a stability; timeline diversity is family-independent by construction; the generator is patched and non-upstream; the A2b gate is non-binding by greedy max-min construction; Level 2 route diversity is tie-break-sensitive; time-respecting reachability permits waiting and is not an OLSR/AODV/DSDV oracle. For every cell the CSV retains the full `2^m` pool vector, including zeros, the full requested-state demand vector, per-pair U and observed run counts, pair fidelity, selected and realized joint-status mismatch counts, and the primary cause. A `missing_requested_statuses` field in prior artifacts means pool count zero only; it is not itself evidence that the assembler used fallback. Selected-pool status differing from requested status is directly observable. Same-status path-ID filter relaxation is not separately exposed in saved artifacts and is not inferred here.

The registered correction-v1 source/result stream hash was recorded upstream as `bb540202500440a0b6f5653f762120f8c0e92893cee344406704219388aa8da9`; A2f-4 did not regenerate or alter those artifacts. The prior result record's 96-file canonical stream was not independently reconciled to the current on-disk file listing in this stage; conclusions here were calculated from the specific read-only per-cell artifacts enumerated in the audit CSV. The initial helper/serialization failure remains an operational probe defect, distinct from the correction-v1 evidence.

## Registered disjoint m=2 pool sweep

All **45/45** child operations succeeded, with no timeout, exception, retry, replacement, or omitted seed. Each had a 60-second wall cap. Maximum wall time was 8.3312 seconds; maximum pool-generation time was 7.0762 seconds; maximum assembly time was 0.2946 seconds. All 45 stored timelines had F=120 and U=60 for both pairs; requested/realized up-run counts are reported descriptively. All 45 assembled edge sets stayed within the fixed ER skeleton. There are 90 per-pair records and 180 full pool-state records. Every per-operation config captures graph/source/prereg hashes and all seed offsets.

The table's requested-state minimum ratio is the minimum, within a seed, of `pool_count / requested_frames` over the requested joint states (`00` and `11`); its column shows the median across five seeds. Pair fidelity uses the registered absolute uptime error limit `<=.05`. “Exact joint frames” counts requested-vs-realized frame matches over 600 requested frames across the five seeds. Mismatch count is selected-pool status differing from requested status; it does not expose same-status PID filtering.

| `p_edge` | Pool trials | Supply-ready ops / 5 | Median min state count | Median min count/demand | Pair fidelity | Exact joint frames / 600 | Selected-status mismatches / 600 | Mean / max wall (s) | Frozen stratum class |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| .3 | 3,000 | 5 | 476 | 7.93 | 10/10 | 600 | 0 (0%) | 1.065 / 1.114 | inconclusive_or_mixed* |
| .3 | 10,000 | 5 | 1,658 | 27.63 | 10/10 | 600 | 0 (0%) | 2.258 / 2.378 | inconclusive_or_mixed* |
| .3 | 30,000 | 5 | 4,965 | 82.75 | 10/10 | 600 | 0 (0%) | 5.649 / 5.820 | inconclusive_or_mixed* |
| .5 | 3,000 | 0 | 3 | .05 | 3/10 | 314 | 286 (47.7%) | 1.228 / 1.353 | inconclusive_or_mixed |
| .5 | 10,000 | 0 | 12 | .20 | 5/10 | 364 | 236 (39.3%) | 2.500 / 2.533 | inconclusive_or_mixed |
| .5 | 30,000 | 0 | 39 | .65 | 5/10 | 508 | 92 (15.3%) | 6.809 / 6.923 | inconclusive_or_mixed |
| .7 | 3,000 | 0 | 0 | 0 | 0/10 | 300 | 300 (50%) | 1.274 / 1.300 | persistent_absence_evidence |
| .7 | 10,000 | 0 | 0 | 0 | 5/10 | 300 | 300 (50%) | 2.960 / 3.048 | persistent_absence_evidence |
| .7 | 30,000 | 0 | 0 | 0 | 5/10 | 300 | 300 (50%) | 7.482 / 8.331 | persistent_absence_evidence |

**Limitations for the sweep table:** life and mean up-run remain confounded under A2a stability; timeline diversity is family-independent by construction; the generator is patched and non-upstream; the A2b gate is non-binding by greedy max-min construction; Level 2 route diversity is tie-break-sensitive; time-respecting reachability permits waiting and is not an OLSR/AODV/DSDV oracle. Full aggregate counts for every status state and their demands, all five per-seed count/demand ratios, runtimes, statuses, and fidelity rows are in [stratum_summary.json](sweep/stratum_summary.json), [stratum_summary.csv](sweep/stratum_summary.csv), [per_operation.csv](sweep/per_operation.csv), [per_pair.csv](sweep/per_pair.csv), and [pool_counts_full.csv](sweep/pool_counts_full.csv).

*At `p_edge=.3`, every trial level already met the operational resolution tests: 5/5 supply-ready operations, 10/10 pair passes, and zero observable mismatches. The frozen label definitions only call `capacity_resolved` when a smaller pool level is unresolved and 30,000 trials resolves it. Since there was no unresolved low-trial level, the literal registered label is `inconclusive_or_mixed`; do not reinterpret it post hoc as a capacity transition. At `p_edge=.5`, the requested `00` pool increased from 14/300 to 64/300 to 208/300 aggregate frames over trial levels, but every seed remained under the 60-frame-per-seed demand; no pool state was absent. At `p_edge=.7`, requested `00` was absent in all 15 operations (including 10,000 and 30,000 trials), giving the registered evidence-limited `persistent_absence_evidence` class. It is not proof that the state is mathematically impossible. The overall preregistered classification is **mixed/inconclusive** because only one of three p-edge strata meets a named class.

The fidelity gate passed 53/90 pairs overall: 30/30 at `p_edge=.3`, 13/30 at `.5`, and 10/30 at `.7`. At `.5`, pair passes were 3/10, 5/10, and 5/10 as pool size increased; the status mismatch count declined, but no operation reached supply-ready. At `.7`, requested all-down state absence persisted; statuses were substituted in 60 frames per operation. These associations do not isolate a unique internal fallback mechanism and are not a protocol-performance result.

## Proposal-only disposition

No change was implemented. If a future separately preregistered engineering task is authorized, the narrow candidate is an **exact-status fail-closed assembly policy**: when a requested joint status has fewer unused pool frames than demand (including zero), return a typed insufficiency record containing requested state, available count, and demand instead of silently selecting Hamming-nearest statuses. Its expected measurable effect is zero selected-status substitutions among successfully assembled frames; under-supplied operations would become explicit failures, not magically acquire fidelity. This would improve diagnostic honesty, not resolve sparse support or guarantee pair uptime. Reusing frames, relaxing quotas, clamping, or generating conditioned frames are different design choices and are not included in this proposal.

A future falsification study should use a fresh isolated copy and preregister exact-state supply cases (enough / nonzero-under-demand / zero), compare legacy and fail-closed policies on fixed stored pools and timelines, and require exact requested-vs-realized status on successful outputs plus typed, exact shortfall metadata otherwise. It should separately measure whether any status-preserving replenishment method can maintain both no-double uniqueness and fidelity before considering that as a different proposal. No A2f-4 result authorizes implementation.

**Limitations for this proposal:** life and mean up-run remain confounded under A2a stability; timeline diversity is family-independent by construction; the generator is patched and non-upstream; the A2b gate is non-binding by greedy max-min construction; Level 2 route diversity is tie-break-sensitive; time-respecting reachability permits waiting and is not an OLSR/AODV/DSDV oracle.

## Reproduction, provenance, and artifact hashes

- Run: `/home/hledirach/Documents/J2/.venv/bin/python /home/hledirach/Documents/J2/simple-graph-experiments-v2/alpha/A2f/A2f-4/run_a2f4.py --audit` followed by `.../run_a2f4.py --sweep`; both were run with the selected Python 3.14.4 environment and NetworkX 2.8.8.
- Audit/sweep driver [run_a2f4.py](run_a2f4.py), SHA-256 `67096963dbe79478c7b96e7dc748ea67f524cb99a7a36c75bdeab0de19678d79` (the source hash recorded in all 45 configs).
- Summary/manifest writer [summarize_sweep.py](summarize_sweep.py), SHA-256 `9107d76be44b3862ce3798516d083e51d504214a42b0b4a7cf4a0d6b1296d6df`.
- Frozen input graph SHA-256 `443ea3ecb243798fb3a6fb97f71a83fc93b8606638d17e7882cd827fafb5ce2b`.
- MPC source hashes in each config: `timelineBlockGenerator.py` `c10fa53afaf4ce323835ed0ffd87de0322b6df7ccc63918c22736b409c13a8a4`; `frameGenerator.py` `e84971f89cb966a574bf447ce8135c0c241b407be14e5066db2f82f3c2ec6b4b`; `dynaGraph.py` `8e75cb59139516bfcc6ccfe672281575c4e8490fdf03d5d5bbcbef8a8b203c42`; frozen original probe `e04f604e5973b386829aa5fa83b66b99d8c9615398c98fe745529a0b36cc7929`; correction wrapper `a64fe73299f59b38b11a2a0bdadaf6fcb96d42d6a7c1346c5c1d5ebb6316a1d7`.
- [classification.json](sweep/classification.json), [operation_log.csv](sweep/operation_log.csv), [per_operation.csv](sweep/per_operation.csv), [per_pair.csv](sweep/per_pair.csv), [pool_counts_full.csv](sweep/pool_counts_full.csv), [stratum_summary.csv](sweep/stratum_summary.csv), [stratum_summary.json](sweep/stratum_summary.json), all 45 configs, and their raw timeline/frame/route/edge/metric files are covered by [artifact_manifest.csv](artifact_manifest.csv), SHA-256 `1e40f83ab27f45d90fa6a926e57b9ca6bdd60bb7f4e5fd85167a8520259c3d8f` (420 entries). The manifest excludes itself and this narrative report to avoid a self-reference; the report hash is logged separately in [gates.md](../../gates.md).

A2f-4 used 0 protocol variants, no ns-3, and no A3. This result makes no OLSR/AODV/DSDV prediction.
