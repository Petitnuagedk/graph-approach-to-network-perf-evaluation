# Phase 7A preregistration — read-only integrity audit

Written before inspecting the Phase 7 audit outcomes. No simulations or edits to Phase 0–6 inputs/artifacts are permitted in this stage. Outputs are limited to this directory and the Phase 7 final report.

## Scope and numeric reporting rules

1. Establish topology/cell provenance from frozen manifests, configs, and serialized trace paths. Pass criterion for provenance completeness: all 15 Phase 6A invocation configs must resolve to exactly one topology and match the manifest’s declared topology; report any mismatch.
2. Count the Phase 5 parameter grid by unique `(topology, path_life, stability, persistency)` tuple, and separately count executions by sweep-cell materialization. Report the center tuple exactly once per topology, with duplicated executions identified. No inferential threshold applies; this is a deterministic count audit.
3. Compare Phase 4 ladder 1-fps and Phase 5 ladder path-life 0.9 realizations. Match trace bytes by SHA-256 and compare all protocol PDRs for corresponding stored result rows. Exact equality means PDR difference ≤ 1e-12 for every matched seed/protocol; otherwise report all mismatches. A missing corresponding Phase 4 cell/seed is a failed match, not an assumed match.
4. Determine shortest-path tie behavior from source and audit results. State whether the implementation uses insertion-order or sorted-label tie-breaking and whether it matches the serialized-trace oracle. Evidence threshold: inspect all six known divergent frames; agreement is exact route-node-sequence equality.

No pass/fail will be assigned to 7A, per request. Stage 7B must use the corrected unique-cell count from item 2. No simulations are authorized by this preregistration.