# A4.3 preregistration amendment 1 — abort, two workers, N=42 only

Written after the user-directed abort and before any new A4.3 launch. The original `prereg.md` is unchanged. This amendment introduces no new physics or simulator flag.

## Correction decisions

1. The in-flight `a43_geodesic_N162_r1_aodv_phi5` attempt was aborted by user direction. Its output directory and logs are retained; its ledger row is `aborted_by_user` with exit code and elapsed time. All prior attempts remain charged.
2. Execution changes from serial to exactly two workers. Each worker launches at most one variant at a time. The A4.0d guard of at least 8 GiB `MemAvailable` and zero swap is checked before each launch. No timeout is installed; the user terminates an overlong process. No automatic retry is permitted.
3. Scope is reduced to N=42 for all five families, AODV and OLSR, and phi in `{1,2,3,4,5}%`: 50 cells. N=92 and N=162 are out of scope after this correction and are not analyzed as A4.3 results. This is a scope reduction, not a measured verdict.
4. Existing completed N=42 geodesic runs are reused only when their exact configuration hash, interpolation-off evidence, readiness, and window match the amended plan. Reused rows are recorded separately. No other old run is reused.

## Gates and unchanged rules

- **G0 PASS:** the read-only A4 runner has `FRAME_RATE = 1.0`, so one frame equals one second. Its positive pair-count rule is `floor(x+0.5)`, i.e. half away from zero, applied to `phi*N*(N-1)/2`.
- **G-A PASS:** `alpha/budget.md` records cap 310 and the user-authorized amendment says the running total before A4.3 is 160. Existing A4.3 attempts are 25 (24 completed plus one aborted), so the total before corrected new launches is 185. Ten completed geodesic N=42 cells are reused, so 40 new launches are planned; the maximum after correction is 225/310. No run may launch if this accounting would exceed 310. `budget.md` is not edited by this correction.
- **G-B PASS:** every new/reused row must verify `--interpolate=false` and the 7B settings: `linkUpLossDb=10`, `linkDownLossDb=125`, `defaultLossDb=1000000`, `lossThresholdDb=150`, `txPowerDbm=20`, `fps=1`, `dataRate=50kbps`, and `packetSize=1024`.
- **G-C PASS:** N=42 uses fixed `T=120 s`; no readiness-driven stop is allowed.

The measurement window remains the original A4.3 rule: `start=max(R+10 s,T/2)`, `end=T`; windows shorter than 60 s are `no_window`. Readiness flags, PDR thresholds, shortfall attribution, and control-amplified attribution are unchanged. Control packets and bytes remain first-class outcomes, split by message type, with AODV RERR separate. No ranking or ceiling language is used; no ddof=1 statistic is used. Additional diagnostics are labelled “written after A4.3 results.”

## Deliverables and stop

The corrected plan is versioned as `plan_amendment_1.csv`; the original `plan.csv` is preserved. The corrected two-worker launcher is `run_amendment_1.sh`; the original `run.sh` is preserved. Per-run output remains CSV-only. A single correction entry is appended to `gates.md`; no prior artifact, prior preregistration, or `budget.md` is edited. Final reporting covers N=42 only, including the abort record, budget ledger, reused and new rows, per-run PDR/MAC/collision values, per-type control bytes and AODV RERR, status matrix, and phi overhead trends. Stop after the report: no N=92/N=162, extra phi, detector/window change, DSDV, or Beta work.
