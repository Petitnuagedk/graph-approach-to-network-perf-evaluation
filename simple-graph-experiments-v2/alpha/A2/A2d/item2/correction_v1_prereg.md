# A2d item 2 correction v1 preregistration — serialization/helper repair

Registered after the failed initial item 2 execution was fully logged and before correction code or any re-execution. This is a separately labeled correction execution, not an unlogged retry. It does not overwrite or supersede the original 18 configs, logs, and failure report; both executions remain reported. Original design and outcome are at `prereg.md` and `results/result.md`.

## Why correction is needed

The first execution revealed a probe/legacy API mismatch: `computeStatistics()` indexes ID-labeled tuples as boolean keys for m=2, and JSON serialization of its tuple-keyed stats fails for m=4/8. The latter 12 operations reached assembly but no per-pair artifacts were persisted. These are probe defects, not evidence of generator incapacity. The correction is limited to replacing that helper call with locally computed JSON-safe requested-timeline statistics and ensuring serializable status-count keys. Do not edit the isolated A0-R2 source tree or change its MPC frame sampler/assembler.

## Frozen replay design

Replay the exact 18 operation cells and seeds in the original item 2 preregistration, in the same cell order, with the same graph, pair sets, 3,000-frame pool, 120-frame timeline, parameters, frame-pool/timeline/assembly seeds, and assembly fallback flags. Execute in a separate `results/correction_v1/` tree and write a new config before each child starts. Record a `correction_version: 1`, both prereg hashes, source hashes, and new runner hash in each config. Each child gets the same 60-second wall timeout; no retries in this correction run. Any timed-out/failed correction cell remains failed and receives no replacement. Never combine first-run failures with correction-run metrics as one sample.

Compute requested per-pair up counts, fractions, and up-run counts directly from `None` versus integer timeline labels; compute status-tuple counts after mapping each path-ID entry to a boolean. JSON keys for joint statuses must be deterministic strings. Persist requested timeline, pool counts, selected indices and statuses, assembled per-frame pair reachability/routes, all frame edges, per-pair uptime errors, and per-operation stage timings before marking the operation successful. Maintain the original graph-skeleton edge subset and fixed endpoints checks.

## Outcomes and thresholds

Apply unchanged the original item 2 thresholds: each operation completes within 60 seconds; all per-pair assembled-uptime absolute errors <=.05; endpoints equal registered sets; every assembled edge is in the fixed ER skeleton. The m=8 tested-limit classification is reached for an arrangement only if its three replay operations all meet runtime and per-pair-fidelity criteria. Report per-seed values and cell mean/sample SD (`ddof=1`) when n>1. Report any assembly fallback/status mismatch descriptively, without inventing a new threshold. Failures from the first execution stay disclosed and do not count as correction successes.

This correction does not authorize A2d item 3, item 4 implementation, A2e, ns-3, protocol variants, or A3. Log the correction result before proposing any next-stage preregistration. Total protocol variants remains 0.
