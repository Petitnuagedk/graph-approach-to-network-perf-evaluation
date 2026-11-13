# A4.2 continuation addendum — complete remaining N=162 cells

**Registered 2026-10-14 in response to the user's explicit instruction to continue A4.2 even if the corrected 60-run projection exceeds 24 hours.** This addendum supersedes only the 24-hour *checkpoint stop* for the remaining cells; it does not alter the initial projection gate, per-run 3,600-second timeout, serial execution, resource guard, one-attempt/no-retry policy, fixed inputs, outcomes, analysis thresholds, or the prohibition on A4.3.

## State and authorization

The repair-v1 stage contains 60 successful, once-only A4.2 results (the full N=42 and N=92 grids). The frozen checkpoint estimate after those runs was 30.925746 hours, so the original runner correctly stopped and did not launch the remaining 30. This addendum preserves that historical stop and authorizes **exactly the 30 remaining N=162 cells once each**, in their original planned order. The previous 60 results must be reused as observations, not rerun. No retries, substitutions, or changes to any completed result. No A4.3.

The current user instruction authorizes exceeding the 24-hour checkpoint projection. Initial projection remains subject to its existing gate and must still be finite and <=24 hours. Any updated checkpoint estimate over 24 hours is recorded and may not stop this specifically authorized continuation. Per-cell resource checks and 3,600-second timeouts remain binding. A failed guard stops all later cells; a started failure/timeout is charged and is not retried.

## Provenance and accounting

Use repair-v1's successful pilot endpoints, AODV corrected binary/source identities, original 90-cell plan, and initial per-cell runtime estimates without recalculation or modification. Before any simulator launch, verify the 60 prior rows are unique and successful, their sequence/run IDs match the frozen first 60, all remaining rows are exactly the 30 preregistered N=162 checkpoint-stopped cells, and all simulator identities match repair-v1. Write new outputs only in this `continuation_v2/` directory; reference the prior 60 raw run folders read-only. Preserve the historical repair-v1 report, ledgers, and manifest.

Charge only new simulator invocations: prior cumulative spend 135/300 + at most 30 continuation attempts = **165/300 maximum**. The completed A4.2 dataset will comprise 90 unique cells, with 60 previously successful results plus up to 30 new attempts. Do not begin A4.3 under any circumstance.
