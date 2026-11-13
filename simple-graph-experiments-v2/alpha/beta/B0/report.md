# B0 follow-up report: timeline and trace audit

The requested re-score cannot be made. A timeline is present in all 30 A4.4 runs, so B0 stops under the user's rule.

- Every run configuration has no explicit `timeline`, `trace`, `path_life`, `stability`, or `persistency` field.
- Every run configuration has a `frames_csv` field and `static_oracle_mode: "frame"`.
- Every run's `process.log` records `Loading frames from ...`, `Trace replay (matrix-based connectivity)`, and `apply_frames=420`, `480`, or `620`.
- No process log contains an `ns-3` or `ns3` invocation. The evidence supports a frame trace passed to the matrix-based replay process, not a trace argument passed directly to ns-3.
- The 15 unique frame inputs have different SHA-256 hashes for their first and second N-row frame blocks. Therefore they are time-varying frame sequences, not repeated static matrices.

The per-run record is in [timeline_audit.csv](timeline_audit.csv), and the detailed evidence and 15 input-level comparisons are in [timeline_audit.md](timeline_audit.md).

## Gate disposition

- G0 remains PASS.
- G1 remains PASS.
- G2 is not applicable only to the absent explicit generator fields, but it is not rescored as N/A for the campaign claim: the static-design contradiction makes the earlier G2 failure real.
- G3 is not rescored as N/A: dynamic frame input exists while path-life, stability, and persistency remain unrecorded.

No B1 authorization is issued. No Alpha, Beta, or A4.4 source record was modified.

## Adapted B0 disposition — F=300

- G0: PASS unchanged from the existing B0 record.
- G1: PASS unchanged from the existing B0 record.
- A4.4 remains a dynamic frame replay with unknown producer and parameters; it is not the Beta reference.
- G2: PASS for the exported Beta copy. The four required module hashes match `source_provenance.json`, the tree is `32b243bc84b587f1782ead0d0ac56382a57425e5`, and `behavior="patched"` is required.
- G3: N/A for A4.4; Beta parameters are recorded per run.
- The F=300 table has 100 cells: 67 feasible, 23 `infeasible_not_run`, and 10 static-reference rows at life 1.0. Persistency does not enter feasibility.
- The existing zero-cost smoke evidence records `ValueError` for an infeasible exact timeline. No substitution or clamp is authorized.
- B1 is BLOCKED because A4.5 has no completed seed-42 AODV/OLSR result; its 30 attempts stopped at the zero-swap pre-launch guard. No B1 run was launched.
