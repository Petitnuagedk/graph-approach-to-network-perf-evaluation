# B1 gate record

## Status amendment — 2026-11-13

- Baseline prerequisite: **PASS**. A4.5 contains completed static N=42 seed-42 AODV/OLSR references.
- Launch authorization: **GRANTED for B1 only** by explicit user instruction.
- Execution: **PASS**; both registered harness checks completed successfully.

## B1 result — 2026-11-13

- AODV: **PASS**, exact match against `a44_geodesic_N42_r1_aodv`.
- OLSR: **PASS**, exact match against `a44_geodesic_N42_r1_olsr`.
- Configuration identity: **PASS** for both protocols.
- Frame/input hash: **PASS** for both protocols.
- Probe PDR, background median PDR, and control totals: **PASS** for both protocols.
- B1 gate decision: **PASS**.
- Next gate: B2. No B2 or sweep run was launched.

- Baseline prerequisite: **STOP**. A4.5 has no completed seed-42 AODV/OLSR result.
- Harness equivalence: **NOT RUN**. No hashes, PDR values, or control totals were compared.
- Launch authorization: **DENIED** for this preparation stage.
- Reason: A4.5 stopped all 30 attempts at the zero-swap pre-launch guard; the existing Beta cap also conflicts with the registered 600-variant Phase 1 plan.

No simulator or protocol process was started.

## Historical-status clarification — 2026-11-13

The preceding STOP/NOT RUN record is retained as historical preparation-stage context and is superseded by the PASS record above. The authoritative B1 decision is PASS.
