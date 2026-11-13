# A2i result — disjoint multi-pair timeline fidelity

## Scope and integrity

The preregistration was written before measurement. SHA-256: `e0e4d0c41f5ca5e2755ec9de25c56b7dd377206e3bc044e605a875ed67becd3a`. Work used an isolated copy of A0R2 YaDyGaGa only; no protected source, prior result, ns-3, graph-run, or protocol operation was changed. The fixed input skeleton hash is `443ea3ecb243798fb3a6fb97f71a83fc93b8606638d17e7882cd827fafb5ce2b`. Known-answer tests passed: four-state uptimes `(0.5,0.5)`, always-up/down `(1.0,0.0)`, and ID-label conversion.

The frozen baseline grid contained 81 child operations. 67 completed and 14 timed out at the registered 60-second wall limit; there were no retries. Baseline outputs and all fix outputs are covered by [output_manifest.sha256](output_manifest.sha256), SHA-256 `c625834ceb14edc40d38e32e09ac1f790f2f61186b802a60a3e432ad87c41e4f`.

## Findings

- **H1 supported.** At p=.5, m=2, fidelity was 0/3 at 3,000 and 0/3 at 30,000, then 3/3 at 300,000; requested `00` counts for seed 11 were 41 and 417, respectively. At p=.3, m=8, fidelity was 0/3 at 3,000 and 3/3 at 30,000. These are direct budget-response observations.
- **H2 supported as finite-sampling scarcity/absence evidence, not impossibility.** At p=.7, the requested all-down state was absent at the largest completed budget for 2/3 m=2 seeds; all three seeds were absent at 3,000 and 30,000. At p=.5, requested states were absent in 3/3 m=4 and 3/3 m=8 operations at 3,000. The 300,000 p=.7 cells mostly timed out; no mathematical nonexistence claim is made.
- **H3 not supported as the primary cause.** When both requested states had sufficient candidates, e.g. p=.3,m=8,t=30,000, sequence divergence was 0 and fidelity was 3/3. Empty-graph substitutions were 0 in all 67 completed baseline operations. The recorded selected-status mismatch counter was invalid because it compared boolean selected statuses with ID-labeled timeline entries; it is excluded from conclusions.

## Joint-state and horizon summary

Each timeline requested only all-down and all-up for these synchronous cells (60 frames each). Representative requested-state counts and outcomes:

| p | m | trials | fidelity | zero requested state | sequence divergence |
|---|---:|---:|---:|---:|---:|
| .3 | 2,4 | 3,000 | 3/3 | 0/3 | 0/3 |
| .3 | 8 | 3,000 | 0/3 | 0/3 | 3/3 |
| .3 | 8 | 30,000 | 3/3 | 0/3 | 0/3 |
| .5 | 2 | 3,000 / 30,000 / 300,000 | 0/3 / 0/3 / 3/3 | 0/3 / 0/3 / 0/3 | 3/3 / 3/3 / 0/3 |
| .5 | 4,8 | 3,000 | 0/3 | 3/3 | 3/3 |
| .7 | 2,4,8 | 3,000, 30,000 | 0/3 | 3/3 | 3/3 |

At p=.7 and 300,000, m=2 had 0/3 fidelity and 2/3 zero-state cells before the remaining cells timed out. Counts for every operation are in the per-operation JSON artifacts and the output manifest. No population SD was used; no aggregate SD was needed for the decision table.

## Assembly audit

The assembler's `force=True` Hamming/any-frame fallback changes status when an exact pool is unavailable. In the p=.5,m=2,30,000,seed=11 case, requested `00` had 41 candidates, yet the realized sequence diverged at frame 101 and pair-B uptime error was `.15833`; at 300,000, `00` had 417 candidates and divergence was zero. At p=.7,m=2,30,000, the requested `00` state was absent, divergence was 60 frames, and pair-A error was `.5`. No empty graph was substituted in completed baseline runs. This supports a budget/supply cause, not an independent path-ID mapping defect.

## Isolated candidate fix

The isolated patch adds `generateMPCFramesForTimeline()` to [frameGenerator.py](src/yadygaga/frameGenerator.py). It regenerates the same seeded prefix through the preregistered ladder and raises explicitly at the 300,000 cap if every requested state does not meet timeline demand; it never silently relaxes status. Patch SHA-256 is recorded in [hash_manifest.txt](hash_manifest.txt). The normalized unified diff dry-run passed; [dry_run_apply.txt](dry_run_apply.txt) records the check.

Fix validation was started in separate [results_fix](results_fix/) output. 10/27 child statuses were emitted and 9/27 produced metrics before the validation process was stopped to write this report; therefore the fix is **not accepted** as a frozen-grid result. Among those nine completed cases, the adaptive method selected an explicit budget and preserved exact realized statuses, but the full disjoint grid and the required shared-source regression were not completed. The prior A2d correction-v1 result remains the shared-source preservation reference: 42/42 shared-source pair checks passed; it was not rerun or modified here.

## Limitations and decisions

This is one N=92 ER skeleton, three disjoint configurations, three seeds, and three p values; timeout-heavy 300,000-trial cells limit the largest-budget evidence. The result does not establish a general pair-capacity limit or a general fix. Decide whether to authorize a separately preregistered completion of the fix validation, whether to replace the status-changing fallback with the fail-closed adaptive method, and whether any future work may proceed. Stop here; no A3, ns-3, or protocol work was started.
