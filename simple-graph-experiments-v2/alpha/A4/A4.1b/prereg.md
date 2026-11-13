# A4.1b preregistration — offline convergence, gap, and warm-up reconciliation

**Registered before any A4.1 run log or per-run output is read.** Scope is offline analysis only under `alpha/A4/A4.1b/`; zero protocol variants, no ns-3 invocation, no simulator, no reruns. Do not edit A4.0*/A4.1 artifacts, the A4.1 preregistration, or amendments. One separate entry may be appended to `alpha/gates.md`. The stage budget remains 70/300; no later stage is authorized.

## Inputs and frozen rules

Use the 45 completed A4.1 run directories, ledger and existing derived rows read-only. Use the exact convergence detector text in `alpha/A4/prereg.md` and the A4.0d readiness definition adopted for A4.1: unique schedule-matched probe receptions; $G=1$ s; trailing 10-s window; minimum observation age 10 s; readiness time is the beginning of the final contiguous passing suffix. Match a probe packet by its frozen app-Tx schedule (first Tx at 0.1 s and 1024-byte packets at 50 kbps, hence 0.16384-s intervals); do not treat a global callback sequence as a per-flow identity. Preserve censored/NaN values as recorded; never impute for correlation or warm-up.

G1: recompute readiness for each of 45 runs and compare with `derived_4.1_runs.csv` `convergence_s`; match tolerance is absolute difference ≤0.5 s, with NaN matching NaN only. PASS iff all 45 match. Otherwise report mismatch count and assign each mismatch one cause: (a) stale input (computed from pre-correction gaps), (b) extra undeclared condition, (c) implementation bug. Determine source hash and read dependencies of the implementation that produced the existing derived convergence.

G2: for each run whose corrected longest post-first-delivery gap is ≤1 s, require recomputed readiness ≤ first-delivery time +10 s. Report every violation. G2 passes iff there are none.

G3: a protocol × N warm-up is valid only if G1 and G2 pass for every contributing family run and no contributing run is censored under the registered >180-s-or-NaN rule. Otherwise report `invalid_pending_detector` for a detector gate failure, or `not_derivable_censored` when detector gates pass but any contributing run is censored. Do not replace either state with an imputed warm-up.

All thresholds and definitions above are fixed before analysis. Any additional descriptive diagnostic must be labelled **“written after A4.1b results”** and may not alter the frozen gates.

## Frozen diagnostics and outputs

1. Reconcile source code path, source hash and whether convergence used pre- or post-correction gap/loss inputs. Test the apparent 113–115-s AODV cluster for shared timestamp/event and any PDR-window or loss rule absent from the written readiness detector. Produce one per-run CSV with first delivery, recorded convergence, recomputed readiness, corrected max gap, gate flags and source/identity details.
2. For all 15 DSDV runs, test whether any gap starts within ±0.5 s of a positive multiple of 15 s; retain all matching starts and gap lengths. Report max-gap empirical distribution for all 45 runs, including counts, median, p90 and maximum. Keep the strict >5-s DSDV exclusion unchanged. Do not claim comparison/comparability with Phase 6D's 15-s outage because warm-up and propagation setups differ.
3. For BA/OLSR N=162, summarize per-node control packet/byte counters by message type, MAC retries/drops, PHY drops by reason, queue drops and forwarded packets over 110–150 s only if timestamped source records support that interval. Compare to equal-length windows within the same run. If any requested counter has no timestamps or message-type attribution in the stored source, report it unavailable rather than assigning it to a time window. Evaluate hub/probe-path associations descriptively; do not infer causation. Check whether a time-local `control_unparsed_*` measure exists; an all-run counter cannot be assigned to the gap interval.
4. Compute convergence-vs-N/diameter correlations only if G1, G2 and warm-up validity G3 all pass for all contributing cells. Otherwise report no correlations. Never substitute censored values; if permitted, report explicit exclusion/censor handling and n per protocol.
5. List warm-up validity and reason by protocol × N. Give proposal-only options for 4.2 with assumptions, run-length/frame-budget consequences, and variant charge. Select none.
6. Account for planned 4.2 (135) and 4.3 (72) against 70/300; state spare capacity (23) and exactly how many registered 4.2/4.3 cells are touched by each unresolved exclusion/censoring set. Do not decide cell dispositions.

## Deliverables and stop

`report.md` ≤150 lines; `gates.md` contains one A4.1b entry; `run.sh` runs offline analysis only; `MANIFEST.sha256` covers A4.1b outputs and scripts except itself. Per-run and diagnostic datasets are CSV. Stop after these deliverables. No A4.2/A4.3, simulator or source changes, reruns, detector changes, or DSDV/OLSR cell disposition are authorized.
