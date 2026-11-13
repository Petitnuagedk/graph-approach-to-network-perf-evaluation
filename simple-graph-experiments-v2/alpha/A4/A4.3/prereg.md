# A4.3 preregistration — operable-load sweep for AODV and OLSR

Registered before plan generation and before any A4.3 simulator launch. This stage is exactly 150 once-only variants: five A1 families × three sizes × two retained protocols × five phi values. DSDV is excluded by user direction, not as a routing verdict. No prior artifact or preregistration is edited. All A4.3 artifacts are written under this directory, except one appended entry in `alpha/gates.md`.

## Fixed gates before launch

- **G0 — PASS condition:** the read-only A4 runner defines `FRAME_RATE = 1.0`, so one frame equals one second. Its `llround()` is `-floor(-x+0.5)` for negative values and `floor(x+0.5)` otherwise: positive counts are rounded half away from zero, not Python banker rounding. A4 uses `llround(phi*N*(N-1)/2)`. This exact rule is used in `plan.csv`.
- **G-A — PASS condition:** `alpha/budget.md` records the amended A4.3 cap as 310 total Alpha variants and the registered running total before A4.3 as 160; 160 + 150 = 310, exactly at the cap. The source is the user-authorized “Cap amendment (user decision, recorded 2026-10-13)” entry in `alpha/budget.md`. No variant is launched if the frozen accounting would exceed 310.
- **G-B — PASS condition:** every A4.3 invocation is required to contain `--interpolate=false`, the 7B channel settings `linkUpLossDb=10`, `linkDownLossDb=125`, `defaultLossDb=1000000`, `lossThresholdDb=150`, `txPowerDbm=20`, `fps=1`, `dataRate=50kbps`, and `packetSize=1024`. The run harness verifies the emitted run metadata and configuration hash for every successful run; a configuration failure is not launched. A4.2 registered `interpolate=true`; that is a declared deviation and A4.2 results are not compared with A4.3 results.
- **G-C — PASS condition:** fixed total simulation durations are T=120 s for N=42, T=300 s for N=92, and T=500 s for N=162. These values are fixed before the first launch and are not readiness-driven stop conditions.

No timeout is used by the A4.3 harness. The user is responsible for terminating an overlong run. Start time, end time, elapsed seconds, exit code, and configuration hash are logged for every attempted run. Runs are serial, with no retry.

## Design and measurement window

For each family × N × protocol, `R` is the A4.1 readiness value from the read-only `derived_4.1_runs.csv`/`run_reconciliation.csv` record for that family-r1 graph and protocol. The fixed measurement window is `start=max(R+10 s,T/2)` when R is defined, otherwise `T/2`; `end=T`. A window shorter than 60 s is marked `no_window` and is still run. A run is flagged `readiness_after_window_start` when finite R is strictly greater than its window start, and `readiness_undefined` when R is absent/non-finite. Load-effect statements use only unflagged runs with a window.

Phi is `{1%,2%,3%,4%,5%}` for every cell. Background flow count is `llround(phi*N*(N-1)/2)`. Record realized count, offered aggregate background load `flows × 50 kbps`, and offered load per node `2 × flows / N`. The probe is additional. The pass criterion, reported per run and never used to stop the sweep, is probe PDR ≥0.99 and background median per-flow PDR ≥0.95 in the fixed measurement window. All thresholds and extra analysis are fixed in advance; any added diagnostic is labelled “written after A4.3 results.”

A shortfall is `congestion candidate` only when the run has a window, is unflagged, and the same shortfall is absent at the next lower phi. A flagged shortfall is `convergence-affected`; all other shortfalls are `indeterminate`. If control bytes per node rise sharply with phi while probe PDR falls, label the pattern `control-amplified candidate`; do not assign it to routing or MAC without the per-message-type breakdown. Control packets and bytes are first-class outcomes, with per-node mean, maximum, and Gini split by message type; AODV RERR is a separate row/column.

## Execution and outputs

`plan.csv` is created before any simulator launch and contains all 150 rows, including family, N, protocol, phi, realized flow count, offered loads, T, window, and flags. The run harness uses only the A3-registered simulator flags; it does not add a flag. It uses the A1 r1 graph edge lists and A1 probe pairs, a T-frame all-up matrix, routing seed 42, instrumentation, and `dumpRoutes=true` for timing. Interpolation is explicitly off. Raw per-run data are CSV only. The per-run table reports probe PDR; background median and p10 per-flow PDR; delay median and p95; control packets and bytes per node mean, max, Gini by message type; forwarded-load Gini; MAC retries per node max; PHY collision drops per node max; offered loads; and readiness flags. MAC and collision values are adjacent to every PDR row.

The report is at most 150 lines and includes gate verdicts, the plan reference, all per-run rows, the status matrix for each family × N × protocol, control-overhead trends, and proposal-only dispositions for cells with no operable phi or only flagged results. It makes no ranking or ceiling claim, uses no DSDV, and uses no ddof=1 statistic. Stop after this deliverable: no additional phi, detector, window, Beta, or DSDV work.
