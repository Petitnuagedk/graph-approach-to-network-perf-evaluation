# A2f-4 preregistration — offline MPC diagnosis and minimal capacity sweep

Registered after A2f-3 PASS and before reading/transforming A2d item2 correction-v1 results for the diagnosis and before generating any new sweep frame pools. All new code/results/proposal remain in `alpha/A2f/A2f-4/`. Read-only inputs: original failed A2d item2 attempt and separately completed `results/correction_v1/`; do not rewrite either. The two attempts remain separate. No MPC fix implementation, upstream/source edits, ns-3, protocol variants, or A3.

**Frozen sources/input identity.** Read-only correction-v1 18-cell stream SHA-256 from its result record: `bb540202500440a0b6f5653f762120f8c0e92893cee344406704219388aa8da9`. Correction prereg hash `4ec08bbf625b39d9164203c488af193b0fd1a582b480e1bda5cdaccda09a2794`; source-tree label `32b243bc84b587f1782ead0d0ac56382a57425e5`; timeline donor `c10fa53afaf4ce323835ed0ffd87de0322b6df7ccc63918c22736b409c13a8a4`; frame-generator donor `e84971f89cb966a574bf447ce8135c0c241b407be14e5066db2f82f3c2ec6b4b`; MPC assembler `8e75cb59139516bfcc6ccfe672281575c4e8490fdf03d5d5bbcbef8a8b203c42`; correction wrapper `a64fe73299f59b38b11a2a0bdadaf6fcb96d42d6a7c1346c5c1d5ebb6316a1d7`. Probe defect was repaired only in the A2d item2 correction wrapper. Initial failures are not measurements and will not be merged with correction-v1 results.

## Step 1 — read-only classification of all correction-v1 cells

Inspect all 18 operations: arrangement `{disjoint,shared_source}` × m `{2,4,8}` × seeds `{11,29,47}`. Write one row per operation with operation status, full `2^m` pool-state count vector including explicit zeros, requested joint-state counts, requested-state missing list, per-pair requested/realized U frames and uptime, requested/realized up-run counts, timeline quota validity, selected pool status per frame, realized frame status per frame, status-mismatch/fallback frame count, pair fidelity, fallback flags available in the saved artifacts, and exactly one cause class. Use only the saved outputs; do not instantiate a generator or mutate files.

Derive `pool_status_fallback_frame_count = count(selected_pool_status != requested_status)` from each `frame_statuses.csv`; separately count `realized_status != requested_status`. These are observable pool-status substitutions, not a complete trace of all internal fallback branches: the saved version does not expose when a path-ID filter is relaxed back to an exact-status pool, so classify such same-status relaxation as unobservable rather than assume it did/did not occur. Include this instrumentation limitation.

For each cell, determine requested timeline validity from stored timeline path-ID labels after mapping `None` to down: all pair U counts must equal the configured rounded quota (60 at life=.5,F=120), and each per-pair Boolean up-run count must equal the configured rounded A2a stability quota (K=30 under Python round-to-even for stability=.5). Per-pair fidelity is the already frozen A2d item2 error rule `abs(realized_uptime-requested_uptime)<=.05`.

Assign **exactly one primary cause** by this ordered first-match rule:
1. `timeline_quota_invalid` if any stored pair U/K is not its registered quota.
2. `requested_joint_state_absent` if any joint state requested by the stored timeline has pool count zero (including states absent from the sparse source JSON).
3. `requested_pool_supply_below_demand` if all requested states exist but any requested state's distinct pool count is below its requested frame count (`no_double=true` means indices are consumed once).
4. `observable_status_fallback_or_assembly_mismatch` if any selected-pool status differs from requested status or any realized frame status differs, provided earlier pool/timeline rules did not match.
5. `pair_metric_mismatch` if pair fidelity fails but no earlier cause matched.
6. `no_observed_fidelity_failure` otherwise.

This is a diagnostic classification, not causal proof. Step 1 reports availability vs demand separately, even where the first-match label picks one.

## Step 2 — frozen m=2 disjoint supply/fidelity sweep

Run only disjoint pairs `[(0,1),(2,3)]` on ER N=92 realization 1, graph SHA-256 `443ea3ecb243798fb3a6fb97f71a83fc93b8606638d17e7882cd827fafb5ce2b`; F=120, life=.5, stability=.5, synchronous mode, pathPersistency=.75, `no_double=true`, `allow_hamming_fallback=true`, `force=true`. Factorial grid: frame-pool trials `{3000,10000,30000}` × p_edge `{.3,.5,.7}` × five seeds `{11,29,47,71,89}` = **45** child-process operations. Timeline seed is the base seed; pool seed=`seed+10000`; assembly seed=`seed+20000`. Do not adjust timeline, pair order, flags, graph, code, or seeds after seeing results. Generate config before each child. Each operation receives a 60-second wall timeout; on timeout/error mark failed and do not retry, extend, clamp, or replace it. Continue the other registered cells and include every attempted seed.

Per operation persist config with all settings/source hashes; requested timeline and pair quota checks; full `2^2` status-count vector including zero states; requested status demands; selected pool statuses and realized statuses for each frame; fallback/mismatch counts; selected frame IDs/reuse counts; per-pair requested and realized uptime/run counts and errors; graph-edge provenance; stage times; status/error record. Also persist `operation_log.csv`, `per_operation.csv`, `per_pair.csv`, `pool_counts_full.csv`, and configs per cell/seed.

**Per-stratum measures.** For each `(trials,p_edge)` over five seeds, report completed count, per-seed and aggregate full requested-state pool counts, supply-ready operations, minimum requested-state count/demand ratio, mismatch/fallback frame count, exact joint-status realization, pair-fidelity pass count out of 10 pairs, mean/max runtime, and all per-seed errors. Supply-ready means every requested state has at least as many pool indices as requested frames. Pair fidelity remains absolute uptime error <=.05. Do not use a newly chosen threshold on mean fidelity in place of per-pair gates.

**Frozen capacity-vs-structure interpretation, applied per p_edge then summarized across p_edge.** Define resolved at a trial count if at least 4/5 operations are supply-ready, at least 9/10 pairs pass fidelity, and total observable selected-status mismatches across the five traces are <=30/600 frames (5%). Apply these ordered classes:
1. `capacity_resolved` if 3000 or 10000 is not resolved and 30000 is resolved.
2. `capacity_sensitive_unresolved` if not already resolved, the ratio of median (over five seeds) minimum requested-state pool count at 30000 to `max(median minimum count at 3000, 1 frame)` is at least 2, and the number of supply-ready operations improves by at least 2/5. Record when the one-frame floor is used.
3. `persistent_absence_evidence` if not already classified and a same requested state is absent (count=0) in at least 4/5 seeds at both 10000 and 30000. This is evidence of sparse/absent support under these samples, not proof of a mathematically impossible state.
4. `persistent_assembly_mismatch` if not already classified, 5/5 operations are supply-ready at 30000, but fewer than 9/10 pairs pass or observable mismatch exceeds 30/600 frames.
5. `inconclusive_or_mixed` otherwise.

For the overall sweep label `capacity_resolved` or `capacity_sensitive_unresolved` only if that class occurs in at least 2 of 3 p_edge strata; label `persistent_absence_evidence` only if it occurs in at least 2 of 3 strata; otherwise report `mixed/inconclusive`. These are evidence-limited operational diagnoses, not asymptotic capacity guarantees. Preserve all p-edge-specific classifications and outcomes.

## Step 3 — proposal only

After Step 1 and Step 2 are logged, write a proposal-only note identifying a minimally scoped candidate MPC assembly change (if justified) and its expected measurable effect, relevant failure modes, and a future preregistered falsification design. Do not edit/run the assembler or use the sweep as authorization. If evidence is insufficient, state that plainly and make no fix recommendation. No follow-up implementation occurs in A2f-4.

## Required report boundaries

Distinguish the initial probe exception (a helper/serialization defect) from the correction-v1 scientific observations. Do not imply all m=2 states were absent: specifically report zero-count and under-demand pool categories individually. Do not infer fallback internally beyond observable selected-vs-requested status differences. Include source/output hashes, command, per-seed tables, runtime and failure accounting, classifications, and proposal-only disposition. The six carry-forward limitations must appear in every report/table section: life and mean up-run are confounded under A2a stability; timeline diversity is family-independent by construction; generator is patched non-upstream; A2b gate is non-binding because of greedy max-min selection; Level 2 route diversity is tie-break-sensitive; time-respecting reachability allows waiting and is not an OLSR/AODV/DSDV oracle. No protocol variants, ns-3, or A3.
