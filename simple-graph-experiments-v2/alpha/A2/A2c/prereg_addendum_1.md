# A2c preregistration addendum 1 — frozen schedule identity check

Registered 2026-10-09 before A2c trace generation. This addendum adds one provenance check only; it changes no cells, numeric criteria, source, timeout, or threshold in [A2c preregistration](prereg.md).

For every family×life×selected-seed operation, hash the generated 120-bit Boolean schedule and require exact equality with that seed's retained timeline hash in the corresponding A2b `candidate_timelines.csv`. The same `(life, seed)` must therefore produce one identical Boolean schedule across all five graph families. Record per-operation match status and a cross-family schedule identity table. Any mismatch is an implementation/provenance failure; do not substitute or regenerate a schedule. This deterministic consistency check is grounded in the already registered generator arguments and graph-independent timeline sampler, not an observed A2c result.
