# B3 gate record

## Authorization — 2026-11-13

The user requested moving forward after the recorded B1 PASS and B2 PASS. B3 is authorized for the registered N=42, five-family, two-protocol, 70-variant block only.

## Pre-execution status

- B1 prerequisite: **PASS**.
- B2 prerequisite: **PASS**.
- B3 preregistration: **RECORDED**.
- Ten-level policy: **CONFIRMED** for path life, stability, and persistency.
- Materialized B3 ledger: **PENDING**.
- Simulator execution: **NOT STARTED**.
- B4/B5/full sweep: **NOT AUTHORIZED**.

## Frame-pool decision and arithmetic hold — 2026-11-13

- Frame pool: **FIXED** — `p_edge=0.5`, `trials=10000`, `pool_seed=11`; timeline seed is the row seed.
- Prior 310-row arithmetic: **WITHDRAWN** — it omitted the five-family multiplier and double-counted the static life-1.0 reference.
- Literal five-family scope: **1,500 absolute rows** before feasibility filtering; this exceeds the 1,200 cap.
- Ledger and simulator: **BLOCKED** pending explicit resolution of the count/cap conflict.

## Execution amendment — 2026-11-13

- Ledger/preflight: **PASS** — 1,500 absolute rows; 1,100 feasible dynamic, 350 `infeasible_not_run`, and 50 static-reference rows.
- Validation: **PASS** — one authorized dynamic row completed with 420 frames parsed and trace replay exit code 0.
- Full feasible dynamic block: **RUNNING** with the fixed pool and at most two workers.
- B4/B5: **STOPPED**.

The B3 runner must pass a non-simulator smoke/preflight check before the 70-variant block is launched.