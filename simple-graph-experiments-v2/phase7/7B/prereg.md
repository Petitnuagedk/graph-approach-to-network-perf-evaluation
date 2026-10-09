# Phase 7B preregistration — no-interpolation channel verification

Written after the 7A audit was recorded. One 7B B0 simulator run has completed; no source edits have occurred. All generated artifacts, configs, traces, and comparisons are under this directory. The 7A audit found 39 unique Phase 5 parameter tuples across three topologies; the repeated center tuple is not treated as additional conditions.

**B0 accounting amendment (2026-10-08):** after inspecting the already-completed B0 output, the frame-count check below was clarified to distinguish source frame matrices from warm-up frames inserted by ns-3. This is a format/accounting clarification, not a change to the input trace, run settings, or numeric acceptance threshold. The existing output is reused only if its trace hash, parsed source frame count, warm-up calculation, and per-protocol apply counts meet the amended rule; no repeat run is authorized or needed for this clarification.

**Pre-run B1/B2 clarification (2026-10-08, before implementation or B1):** B1 static-vs-oracle error is fixed at absolute PDR minus no-interpolation usable-uptime magnitude **≤0.05 in each of the three alternating-trace down-loss runs**. This per-run criterion is not relaxed after output inspection; a miss means static is not accepted as the dynamic effective-uptime reference. B1 all-up controls use 60 source frames, 1 fps, and zero warm-up; the required ≥0.99 PDR applies to the whole resulting application run (traffic starts at 0.1 s). Require at least 300 offered and 297 delivered packets. This resolves the former sentence that mentioned both zero warm-up and a 45-second warm-up. B2's exact comparison scope is the deterministic outputs: packet-event CSVs and route logs byte-for-byte, plus result CSVs byte-identical after removing only the nondeterministic wall- and CPU-time columns. No protocol counts, packet events, route/channel-state fields, or other deterministic outputs may be ignored. The optional no-interpolation v2 profile is selected explicitly; the absent-profile and explicit legacy path must retain interpolation-on behavior.

## Objective and compatibility contract

The v2 channel profile shall run with `--interpolate=false` by default. Selecting the v2 profile is opt-in. With no new profile option, the legacy pipeline behavior remains interpolation enabled; explicit legacy arguments remain available. This is how the new v2 default and legacy reproducibility will coexist. All Phase 7 run configs will record the resolved interpolation value, explicit down-loss, simulator args, graph/trace/config hashes, pipeline/source hashes, and ns-3 source hashes. No Phase 0–6 output is modified.

This stage reports channel-verification measures only; no cross-protocol comparisons or PDR rescaling will be reported. The static route is used solely to deliver probe traffic over a known one-hop path.

## Planned run batches and budget

Accounting is protocol variants = graph-run invocations × routing variants.

| Batch | Design | Invocations × variants | Budget |
|---|---|---:|---:|
| B0 legacy golden, before source change | One existing 60-frame line trace, `path_life=0.7`, OLSR/AODV/static, legacy interpolation explicitly on | 1 × 3 | 3 |
| B1 synthetic channel | One generated 60-frame, 1-fps single-hop S–R trace, run with explicit down-loss 125, 200, and 1,000,000 dB; static route only | 3 × 1 | 3 |
| B1 all-up controls | 60-frame all-up line and ladder traces, 1-fps, static route only, v2 profile | 2 × 1 | 2 |
| B2 legacy regression | Repeat the exact B0 trace/config/seed/traffic/routing and legacy interpolation, using the post-change pipeline | 1 × 3 | 3 |
| **Maximum for 7B** | **No additional runs without a new preregistration and budget amendment** | **7 invocations** | **11 variants** |

Planned order is B0 (capture before code changes), implement the opt-in v2 profile, then B1 and B2. Each batch is followed immediately by an append-only update to `phase7/budget.md`. The maximum cumulative Phase 7 total after 7B is 11/300; no campaign is authorized.

## Gates and numeric criteria

### Gate B0 — legacy golden capture and frame accounting

- Run one existing line trace with exactly 60 frames at 1 fps, 45-second first-frame warm-up, 50 kbps UDP, 1,024-byte packets, seed 42, and variants OLSR/AODV/static; explicitly set interpolation on and preserve all other recorded settings.
- Capture deterministic replay outputs and source/config hashes under `7B/legacy_before/` before modifying pipeline code.
- Define **source CSV rows** as frame matrices (blank-delimited frames), not physical text lines: each matrix has one row per node. The source trace passes only if it contains exactly 60 such frame rows/matrices, has the expected SHA-256, and resolves to 1 fps.
- Warm-up is inserted as whole frames. Required accounting: `applied_frames = source_frame_rows + ceil(warmup_seconds × fps)`. For this B0 case the expected value is `60 + ceil(45 × 1) = 105` applied frames. The `graph-run` load log and each result row's `frame_apply_calls` must both report exactly 105. The source CSV in its current matrix format is expected to have 300 matrix data rows plus one header (301 nonblank physical lines) and 59 blank separators (360 physical lines total); those text-line counts are a format check, not the number of frames.
- Validity: exactly three protocol rows, 60 source frame matrices, exactly 105 applied frames per protocol, correct trace SHA-256, resolved `interpolate=true`, and successful exit. If any fails, stop before editing. If a prior B0 output has the same input hash, complete logs, and exact counts, it qualifies; do not rerun solely to relabel its accounting.

### Gate B1a — down-loss equivalence and per-frame channel behavior

- Generate one deterministic 60-frame, 1-fps single-hop S–R trace. It consists of 30 repetitions of one up frame followed by one down frame; therefore it includes exactly 30 one-frame up-runs, 30 one-frame down-runs, and 60 frame boundaries. Store and hash the trace and generator/config metadata.
- Probe with UDP at a configured rate that produces at least 20 scheduled packets in every full frame (target at least 100 packets/s), one static route, no dynamic routing protocol, and `--interpolate=false`.
- Run identical trace/seed/traffic three times, setting the down-link loss explicitly to 125, 200, and 1,000,000 dB; keep sparse threshold 150 dB and all other settings fixed.
- Required thresholds for **each** run: at least 20 scheduled packets per full frame; maximum absolute discrepancy between observed usable-interval boundaries and the corresponding integer-second frame boundary ≤ 0.010 s; exactly zero packet deliveries attributed to down frames; binary and usable uptime exactly equal in the C++ oracle and Python recomputation (absolute difference 0 over 60/60 frames); and all-up-frame packet deliveries and per-frame delivery counts identical across all three down-loss values (maximum per-frame count difference 0). Any failure stops 7B.

### Gate B1b — all-up controls

- Run 60-frame, 1-fps all-up line and ladder controls, static route only, with the v2 profile, explicit down-loss 125 dB, 50 kbps UDP, and no warm-up, matching the Phase 6B control traffic/warm-up settings while correcting frame count and time scale. This corrects the 70-frame inconsistency in Phase 6B; both stored traces must contain exactly 60 frames spanning 60 seconds of trace time.
- Required thresholds per topology: trace connectivity is 60/60 up frames; no deliveries are attributed to a down frame; zero warm-up; PDR ≥ 0.99 over the application run; at least 300 application packets are offered and at least 297 delivered. The frozen run parameters and exact packet-count threshold are the pre-run clarification above; the obsolete 45-second sentence does not apply.

### Gate B2 — legacy regression

- Repeat B0 exactly after implementation, explicitly selecting legacy behavior/interpolation on. Compare protocol PDR counts and deterministic packet-level outcomes/routes against B0; exclude wall-clock/CPU-time fields and timestamps that are inherently process-relative, but do not exclude any delivery, loss, route, or channel-state result.
- Required threshold: zero differences in each deterministic field for all three protocols; exactly three rows; trace SHA-256 unchanged; resolved interpolation true; and the post-change invocation must complete successfully. A single deterministic-field difference fails this gate and stops Phase 7 before 7C.

## Stop rule and reporting

7B passes only if Gates B0, B1a, B1b, and B2 each meet every stated threshold. Otherwise record the failing metric and exact difference, update the budget for any completed batch, and stop; do not begin 7C. Report per-run metrics and raw per-frame delivery counts, not just means. If summary statistics are included across runs, use sample SD (`ddof=1`) and do not treat packets or frames as independent realizations. A single trace/run is a verification case, not a population estimate.

No simulator batch beyond the 11-variant plan is authorized. The Phase 7 global budget remains capped at 300 variants, and no campaign launch is authorized.