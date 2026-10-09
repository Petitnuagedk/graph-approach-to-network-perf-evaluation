# Alpha A0-R preregistration — root cause and isolated remediation

**Registered 2026-10-09 before A0-R execution.** A0's recorded verdict in `alpha/A0/yadygaga_capabilities.md` is historical and immutable; this follow-up does not revise it. All work is under `simple-graph-experiments-v2/alpha/A0R/`, on a copy derived from clean YaDyGaGa commit `51b01ac7faa78a494c3baedc560d658f384afe09`. Do not modify/import the dirty YaDyGaGa checkout, dirty `G2DG-SPC.py`, or any existing generator source in the project. No ns-3, protocol runs, A1, or Beta. Cost: 0 protocol variants.

## Frozen A0 thresholds (unchanged)

- Diversity: N=92, 120 frames, path life 0.5, seeds 42–46; require ≥5 unique S–R connectivity bit strings and mean pairwise Hamming fraction strictly >0.10.
- Fidelity: N=92, 120 frames, requested lives 0.3/0.5/0.7, seeds 42–46; every assembled trace's realized S–R uptime must be within 0.05 of requested.
- Timing: N=162, 120 frames, seeds 42–44; each generation time <600 seconds, and every timed trace must have nonempty up and down candidate pools.

No A0 threshold is altered. New A0-R measurements have no pass threshold except these frozen criteria. Trial-count diagnostics are fixed at 500, 2,000, and 10,000 candidates; report a selected minimum only if data justify it. Parameter-coupling grid is stability 0.0/0.4/0.8 and pathPersistency 0.0/0.5/1.0, at N=92, life=0.5, 120 frames, seeds 42–46. Pool checks use p_edge=0.5 and trials=500/2,000/10,000 at N=92 and N=162; report every seed and pool count, group count, wall time, and empty/tiny-pool status. Define tiny descriptively as <5 candidate frames in either relevant pool; this is a diagnostic label, not an acceptance threshold.

## Step 1 — root cause, fixed order

1. Call clean-HEAD `SPCTimelineBlockGenerator.generate_blocks()` directly for seeds 42–46 at frames=120, life=0.5, stability=0.8, persistency=0.9. Save both Boolean timelines and path IDs. Establish whether `seed` changes the Boolean sequence or only path IDs. Cite exact implementation lines.
2. Before any patch, repeat the N=92 assembled S–R bitstream diagnostic at trials=500, 2,000, and 10,000, holding p_edge=0.5, N=92 diameter pair, frames=120, life=0.5, stability=0.8, persistency=0.9, and seeds 42–46 fixed. Record per-run up/down candidate-frame counts, shortest-path group count, S–R timeline uniqueness/Hamming, wall time, and pool-validity. Use a seed-local sampling stream in the diagnostic harness so repeated trial-count comparisons are deterministic and isolated; do not modify the old generator.
3. At trials=2,000, vary stability and persistency over the frozen 3×3 grid; record the Boolean S–R timelines, unique count/Hamming across seeds, realized S–R transitions and uptime, and path-ID transitions separately. Stability effects must be assessed on measured S–R bits, not inferred from `toolbox.timelineFeasibleParams`.
4. At N=92 and N=162, p_edge=0.5, report per-seed up/down pool sizes and path-group count. Flag empty pools and pools with <5 candidate frames. A timed row with an empty required pool is invalid for the timing gate and is reported separately.

## Step 2 — feasible Boolean timeline space; stop rule

Enumerate analytically the number of binary S–R timelines at each `(frames, path_life, stability)` cell for frames ∈{60,120}, path life ∈{0.3,0.5,0.7}, stability ∈{0.0,0.4,0.8}. Use the clean committed generator's rounded up quota and exact stability-to-up-run formula, which has **no cap at `down_count + 1`**. A valid timeline must have exactly the rounded up count and requested up-run count. If the requested up-run count exceeds `min(up_count, down_count + 1)`, the valid exact-quota timeline count is zero; the source may then truncate/pad and fail the quota. Otherwise the count is `C(up_count-1, up_runs-1) * C(down_count+1, up_runs)` for nontrivial cells; verify edge cases explicitly. The maximum achievable mean normalized pairwise Hamming distance is calculated over that finite valid set when enumerable, otherwise via a stated exact optimization or certified bound; do not substitute whole graph differences. Identify how life and stability narrow the space. “Safe region” means cells whose feasible count and Hamming capacity can satisfy the frozen diversity threshold, not a claim that the implementation samples them well.

**Stop before any remediation patch or patched rerun if a frozen-criterion cell is infeasible by construction** (fewer than five valid timelines or maximum Hamming ≤0.10), record the obstruction and wait for the user. Do not relax thresholds. If all frozen cells are feasible, proceed to Step 3.
**Stop before any remediation patch or patched rerun if a frozen A0 acceptance cell is infeasible by construction** (fewer than five valid timelines or maximum Hamming ≤0.10), record the obstruction and wait for the user. The primary frozen diversity cell is `(N=92, frames=120, life=0.5, stability=0.8)`; fidelity and timing cells retain their frozen separate constraints. Report all preregistered feasibility-grid obstructions, but do not treat an unrelated grid diagnostic cell as a frozen A0 acceptance cell. Do not relax thresholds. If the frozen A0 acceptance cells are feasible, proceed to Step 3.

## Step 3 — isolated patch and validation (only after Step 2 passes)

Make and test changes only in the isolated copy under `alpha/A0R/YaDyGaGa/`. Preserve exact rounded up quota and the committed stability-to-up-run target; add seed-driven selection among valid block placements/lengths so different seeds can yield different Boolean S–R timelines while preserving those invariants. Give timeline construction its own seeded RNG stream; do not use global `random.seed()` or an unseeded `Random()` for assembly. Keep frame-sampling RNG independent from timeline and assembly selection. Record source tree hash before/after and deliver the exact patch as `alpha/A0R/yadygaga_a0r.patch`; user decides whether to upstream.

Re-run frozen A0 gates on the patched copy: N=92 diversity (seeds 42–46), N=92 fidelity (three lives × five seeds), N=162/120 timing (three reps, with pool validity). Also test a regression fixture demonstrating byte-identical output for an unpatched code path under the same seed only where that behavior is intended unchanged; specify precisely what fixture/API path is compared. The patch intentionally changes seeded Boolean placement, so do not claim full legacy trace equivalence.

## Step 4 — remaining capability gaps

- Run MPC at N=92 with two disjoint pairs and two shared-node pairs, recording API inputs, returned status/path metadata, counts, and failure behavior. Report demonstrated versus documented maximum.
- Probe out-of-range and infeasible life/stability requests from the documented API. Record exception, clamp, silent relaxation, or realized-constraint violation; do not silently repair the request.
- State that sampled-frame edges are i.i.d. draws from the supplied candidate graph at `p_edge`, with no per-link persistence/lifetime control. Include a design-only Edge-Markovian fallback note scoped to random-link fraction/lifetime: each skeleton edge is a two-state Markov chain with stationary up fraction π and mean up duration L frames, `p10=1/L`, `p01=π*p10/(1-π)`. State the cost: S–R uptime becomes an output, and is confounded with topology unless π is calibrated per family. Do not implement or switch to the fallback.
- Classify Phase 7D `generator_v2.py` as a replacement, wrapper, or fallback relative to YaDyGaGa; retain its tested scope (N=5/8, 60 frames) and do not use it as A0 evidence.

## Required outputs and provenance

Write `alpha/A0R/report.md` with root-cause table (cause/evidence/verdict: seed, horizon, deterministic construction, pool starvation, none), feasibility table, source line citations, patch description and hashes, patched A0-gate results with pool sizes, per-axis verdicts, Edge-Markovian design-only note, exact commands, SHA-256 for all generated result tables, and explicit decisions required from the user. Record in `alpha/gates.md` the SHA-256 of this prereg, its gate, the A0 historical-prereg dedup hashes, both generation-wrapper hashes (A0 worker `eafb56abf7482f90aed77f56ea2a9e19fc198156c9fb02efc90dc3e631c6cbec`; aggregation-only wrapper `77aac3c876a7d484bfb6b232bd48d6bb9d79cdc47dc97fd0acd72ebf3186f75b`), and the clean source snapshot tree identity. The original `/tmp/yadygaga-alpha-a0-clean` was removed after A0; label its original materialized-tree hash unavailable. Reconstruct and hash a new clean snapshot from Git only after preregistration, and clearly distinguish its reproducible tree identity from the removed snapshot.

## Stop boundary

A0 remains failed as recorded; A0-R is a separate diagnostic/remediation follow-up. Stop and wait if feasibility fails, a source-file edit outside the isolated copy is required, ns-3 would be needed, or any frozen threshold would need to change. Do not start A1 or Beta; total protocol variants remain zero.
