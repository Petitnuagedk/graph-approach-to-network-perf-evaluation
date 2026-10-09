# Alpha A0 preregistration — YaDyGaGa capability and scale audit

**Registered 2026-10-09 before beginning A0 source inspection or scale generation.** A0 is read-only with respect to existing project/library source and experimental inputs. It authorizes source/document inspection and generator-only trace construction/measurement, but **zero `graph-run` invocations, zero protocol variants, no A1 work, no edits to existing generator files, and no use of an unapproved modified generator path**. All new A0 outputs go under `simple-graph-experiments-v2/alpha/A0/`. If the exact upstream generator and a non-mutating way to exercise it cannot be identified, report the blocker rather than substitute another generator silently.

**Execution-path clarification (2026-10-09, before any A0 generation measurements; thresholds unchanged):** the YaDyGaGa working checkout has uncommitted changes in `timelineBlockGenerator.py` and `toolbox.py`, and J2 has a separate uncommitted `G2DG-SPC.py` change. Do not import/execute those dirty files. The governing Alpha campaign explicitly permits all adaptation in new wrapper modules under `alpha/` and prohibits changing existing generator files (docs/Alpha campain.md, lines 11–15). Accordingly, an A0-only wrapper may exercise the pristine YaDyGaGa HEAD (`51b01ac7faa78a494c3baedc560d658f384afe09`) from an isolated temporary source snapshot created from Git, with no edits to existing source and all new wrapper/results under `alpha/A0/`; it must not import or execute modified `G2DG-SPC.py` or the dirty checkout modules. This documented authorization resolves the execution-path question; thresholds, seed lists, scale cells, and acceptance rules above remain frozen. If the isolated pristine-source route fails technically, stop and record the specific blocker; do not silently switch source versions or substitute Phase 7D evidence.

## Sources and implementation comparison (frozen scope)

1. Locate the YaDyGaGa library, its documentation, version or source hash, and the exact API/file interface that Alpha would invoke. Trace the implementation paths for timeline construction, constrained paths, random links, seed use, outputs, and infeasibility handling. Cite repository-relative file paths and 1-based line ranges in the A0 report for every source-based claim.
2. Inspect the current `G2DG-SPC.py` worktree file and compare it read-only to the repository's checked-in `HEAD` version. Record the exact SHA-256 of each, `git diff -- G2DG-SPC.py`, and semantic changes relevant to RNG streams, S–R timeline construction, path-pool generation, frame assembly, persistency, and caller/API boundaries. Do not modify, stage, revert, import, or execute this file for the A0 tests. Distinguish the new Phase 7D `generator_v2.py` adapter from both YaDyGaGa and `G2DG-SPC.py`; do not treat its small-topology result as upstream capability evidence.
3. Identify the approved generator entry point for A0. If the only available route would execute a modified legacy `G2DG-SPC.py`, stop before executing it and report that the no-existing-generator-edit rule/provenance blocks the run pending user review. Source inspection itself may still be completed.

## Fixed generation and measurement design

- Use the exact Alpha geodesic size formula: $N=10\nu^2+2$ for $\nu=2,3,4$, producing N=42, 92, and 162. Use one deterministic geodesic skeleton per size unless the upstream interface requires otherwise; disclose any unavoidable deviation.
- For each N, construct traces at frame counts 60 and 120. Measure three independent repetitions per (N, frame count) cell. Use fixed, recorded seeds 42, 43, and 44; use identical seed lists across sizes/frame counts. Do not choose or replace seeds after observing outputs.
- For every trace record elapsed monotonic wall time, peak resident memory, output byte count, generator source/version hashes, arguments, seed, requested and realized parameters, and output SHA-256. Time trace generation only; do not include graph-run or downstream simulation. Report all three measurements per cell and mean/median/max; do not treat repetitions as network-performance realizations.
- For N=92, path life requested values are exactly 0.3, 0.5, and 0.7 at 120 frames, five distinct preregistered seeds 42–46 per condition. Measure the serialized S–R connectivity bit timeline (one bit per frame), requested/realized uptime, distinct count, and mean pairwise Hamming fraction. Use no whole-matrix diversity surrogate.
- For N=92, path life 0.5, 120 frames, independently generate five seed-specific S–R timelines (seeds 42–46) and assess seed diversity. This condition is also the A0(c) acceptance case; it is not a new sixth seed set.
- To characterize controls at the same N=92/120-frame condition, inspect and, where the identified interface supports them, run a preregistered 2×2 diagnostic for random-link fraction and lifetime (low/high settings explicitly mapped to API values). If the generator offers no separate parameters, record that fact as a capability limitation rather than inventing flags. Keep the S–R path specification fixed while measuring whether each control is independently variable.
- No graph-run, ns-3 replay, network traffic, protocol variant, A1 graph-family generation, or instrumentation changes are allowed in A0.

## Frozen numeric decision rules

A0 reports one verdict per axis: path life, stability, persistency, random-link fraction, random-link lifetime, and number of constrained paths; each verdict must cite the source/measurement evidence.

**Seed diversity (stop-critical):** at N=92, path life 0.5, 120 frames, five distinct seeds, require at least 5 unique S–R bit strings and mean pairwise Hamming fraction **strictly greater than 0.10**. Whole-trace/matrix differences do not count. Failure means `not usable` for seed diversity and stop for user review.

**N=162 generation time (stop-critical):** for each of three repetitions at N=162, 120 frames, require generation elapsed time **<600 seconds**. Any repetition at or above 600 seconds fails this criterion. Also report the 60-frame timing cell but do not substitute it for this gate.

**Requested path-life fidelity (stop-critical):** at N=92 and 120 frames for requested path life 0.3, 0.5, and 0.7, require the absolute difference between realized S–R usable uptime and requested path life to be **≤0.05 for every preregistered seed**. Missing or infeasible cases count as failures, not exclusions. Failure means `not usable` for path life and stop for user review.

**Capability-axis classification:**
- Path life: `usable` only if the source/API exposes the control and the N=92 fidelity rule passes; otherwise `partly usable` only if it exposes a documented, measurable approximation, else `not usable`.
- Stability and persistency: `usable` only if independently controllable as documented and verified not to be an alias for another parameter; `partly usable` if controllable but coupled/limited; otherwise `not usable`.
- Random-link fraction and lifetime: `usable` only if both can be independently set or independently characterized by measurements; `partly usable` if only one exists or they are coupled; otherwise `not usable`.
- Number of constrained paths: report maximum demonstrated/documented count and shared-node support. `usable` requires at least one path; `partly usable` means one path only or a documented restriction; `not usable` means no constrained path can be specified.
- Infeasibility: test only documented/available controls; report whether invalid or infeasible requests error, reject, silently relax, or produce a trace that violates the requested constraint. Never silently change a request to make it pass.

Overall A0 is `usable for Beta` only if the Alpha document's conditions (a)–(e) all pass: at least one constrained probe path; random-link behavior documented/measured with two separable controls or characterized fraction/lifetime; seed diversity above; N=162 120-frame trace generation under 10 minutes; and N=92 path-life fidelity at 0.3/0.5/0.7. Otherwise give a precise `partly usable` or `not usable` verdict by axis and stop for user review if path life or seed diversity is not usable. No switch to Edge-Markovian fallback without an explicit design note and user decision.

## Stage boundary

A0 completion requires `yadygaga_capabilities.md`, the per-axis verdict/evidence table, source/hash inventory, G2DG-SPC comparison, raw generation timing/memory table if the approved upstream entry point is available, and a concise decision record in `alpha/gates.md`. Do not start A1 until the A0 verdict is recorded and the user authorizes continuation. A0 costs **0 protocol variants**. Beta's cap unit is protocol variants, but no Beta numeric cap is set here.
