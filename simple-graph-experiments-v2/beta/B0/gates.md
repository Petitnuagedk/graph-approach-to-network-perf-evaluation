# B0 follow-up gate record

**Date:** 2026-11-12

- **G0 — PASS unchanged.** All 30 A4.4 run configuration records were present.
- **G1 — PASS unchanged.** All 30 run configurations report interpolation OFF and the 7B channel settings.
- **G2 — STOP/FAIL, not N/A.** The run configurations omit explicit timeline/generator fields, but every run has `frames_csv`; every process log reports matrix-based trace replay and applies 420, 480, or 620 frames. The first and second frame blocks differ for every unique family-size input. This contradicts the static all-links-up claim. No ns-3 invocation is evidenced in the process logs.
- **G3 — STOP/FAIL, not N/A.** Path-life, stability, and persistency fields are absent, but dynamic frame input is present and changes over time. They cannot be treated as inapplicable to the observed execution.

## Adapted Beta preparation gate — 2026-11-12

- G0: PASS unchanged.
- G1: PASS unchanged.
- G2: PASS for the exported pinned Beta copy; required module hashes and `behavior="patched"` are recorded in `source_provenance.json`.
- G3: N/A for historical A4.4; Beta parameters are recorded per run.
- Feasibility: 67 feasible cells, 23 `infeasible_not_run` cells, and 10 life-1.0 static-reference cells.
- The existing zero-cost infeasible smoke evidence raised `ValueError`; no substitution occurred.
- B1 remains blocked by incomplete A4.5 static reference records.
- The 600-variant Phase 1 plan exceeds the existing 500-variant Beta cap; stop and report, with no silent reduction or cap change.

## Execution amendment — 2026-11-13

- A4.5 completion supersedes the earlier incomplete-reference status: the amended ledger contains 30/30 successful static runs, including the required N=42 seed-42 AODV and OLSR rows.
- The user raised the Beta cap to 1,200 protocol variants. The 600-variant Phase 1 design is within that cap; Phase 2 remains separately capped.
- B1 was explicitly authorized and is the only stage launched under this amendment.

No Beta protocol run was launched.

**Decision:** Stop B0. Do not authorize B1. The detailed per-run evidence is in [timeline_audit.csv](timeline_audit.csv) and [timeline_audit.md](timeline_audit.md).
