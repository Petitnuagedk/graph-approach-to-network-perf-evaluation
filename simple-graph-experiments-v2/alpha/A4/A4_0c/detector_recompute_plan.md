# A4.0c detector recompute plan — frozen before final recomputation

The first exploratory offline replay exposed that the original suffix detector returns the last probe Rx event in the three raw-log runs and that candidate thresholds are feasible. Treat those first candidate numbers as exploratory only; the final recomputation is the reportable pass.

## Definitions fixed for the final recomputation

1. **Original**: exact `ProbeConvergenceTime` semantics in the protected source, 10-second windows, `unique Rx event count / Tx event count >= 0.99`, evaluated at each probe Tx/Rx event and each event's +10-second expiry, with the earliest point in the final contiguous passing suffix returned.
2. **Corrected-original**: retain the same 10-second window, event boundaries, suffix rule, and 0.99 threshold, but omit a Tx from the denominator until it has aged one configured packet interval, Δ = 1024×8/50,000 = 0.16384 s at that evaluation. Count its matching unique Rx only if received by that evaluation. This prevents an immediately outstanding packet from acting as a loss. No other retuning.
3. **Candidate C95 (primary)**: corrected-original maturity rule and event/suffix rule, but threshold 0.95. At roughly 61 offered packets per 10 s, this tolerates up to about three losses per window, so one isolated MAC loss does not reset the detector while sustained delivery collapse still fails.
4. **Candidate C90 (sensitivity)**: same as C95 at 0.90. It is intentionally more permissive and is not eligible for selection if C95 passes all tests.

**Selection rule fixed before final recomputation:** choose the strictest of C95/C90 that passes the three frozen T3 expected outcomes (10 s, 24 s, NaN), the in-flight-tail synthetic (finite before last-Rx time), and the single-random-loss synthetic (finite and no later than the no-loss readiness time); also reject any candidate whose computed readiness equals the final Rx timestamp when earlier readiness exists. If C95 passes, select C95; otherwise test C90 against exactly the same criteria. These candidates are diagnostics, not replacements for a preregistered acceptance gate; user approval is required before using one in A4.1.

## Input limitation

The A4.0B validation directories have `packets_<protocol>.csv` Tx/Rx timestamps. The successful A4.0A pilot directories do not: `dumpRoutes=false`, and their persisted files contain no per-packet timing sequence. For those pilots, the original/corrected/candidate windows and last-loss time cannot be recomputed; report them unavailable rather than fabricate. The offered count yields scheduled final Tx time only. Saved finite convergence minus that scheduled Tx is an implied delay, not independently verified.
