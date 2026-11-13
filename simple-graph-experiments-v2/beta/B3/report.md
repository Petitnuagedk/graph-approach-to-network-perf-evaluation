B3 is superseded by the MPC transition recorded in [MPC_transition_2026-11-13.md](../MPC_transition_2026-11-13.md). The SPC block is cancelled; completed SPC outputs are audit-only.
# B3 report

## Status — 2026-11-13

B3 has been authorized and preregistered for the 70-variant N=42 one-axis block. B1 and B2 reports are recorded and pass their gates. No B3 simulator run has started yet; the materialized ledger and runner preflight are the next required artifacts.

The user subsequently amended the block to use ten levels for each of path life, stability, and persistency. The N=42 absolute ledger is therefore 310 rows: 300 dynamic rows plus 10 static-reference rows. Infeasible rows will be retained as `infeasible_not_run`. The previous 70-row description is historical and superseded.

B4, B5, and the remaining Beta sweep remain stopped.

## Execution amendment — 2026-11-13

The user authorized B3 execution after selecting the single A2 pool. The ledger and non-simulator preflight passed: 1,500 absolute rows, comprising 1,100 feasible dynamic rows, 350 `infeasible_not_run` rows, and 50 A4.5 static-reference rows. The runner was corrected to pass ns-3's required argument separator and to emit blank-separated 42×42 frame matrices. A one-row validation completed successfully with 420 frames loaded and ns-3 trace replay completed. The full feasible dynamic block is now running with at most two workers; no B4/B5 work has started.

## Frame-pool decision and arithmetic hold — 2026-11-13

The selected B3 frame pool is fixed at `p_edge=0.5`, `trials=10000`, `pool_seed=11`; no other A2 pool configuration is included.

The previously recorded 310-row count is withdrawn as non-executable: it omitted the five-family multiplier and double-counted the life-1.0 static reference. The literal registered scope yields `5 × 2 × 5 × 30 = 1,500` absolute rows (29 dynamic levels plus one A4.5 reference per family/protocol/seed), which exceeds the 1,200 cap. B3 remains on arithmetic hold; no ledger or simulator execution has started.