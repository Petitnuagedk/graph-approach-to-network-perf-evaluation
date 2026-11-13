# A4.2 repair-v1 addendum 3 — bounded AODV retry counter and replacement endpoint

**Registered after the diagnostic result and before source edits/build/pilot invocation.** The historic A4.0A failure, repair-v1 AODV replacement failure, and diagnostic failure remain failed attempts; no elapsed process time from any of them is a valid completed runtime.

## Diagnostic finding

The authorized diagnostic replay reproduced the assertion at `t=24.000100000 s` and emitted: destination `10.1.0.155`; route hop `35`, diameter `35`; AODV RREQ count `32` while `RreqRetries=2`; node traversal `40,000,000 ns`; net traversal `2,800,000,000 ns`; timeout buffer `2`; full-diameter branch; computed backoff factor `31`; computed retry `−6,012,950,000,000,000,000 ns`. This establishes that the failure is signed-shift overflow in the full-diameter retry calculation after the request counter exceeded its configured retry limit. The current code's `1 << (RreqCnt−1)` invokes signed-int overflow/undefined behavior at count 32; the counter is stored in a wider unsigned route-table field, and repeated route-request scheduling allowed it to exceed configured `RreqRetries=2`.

## Authorized source repair and one replacement run

Authorize a narrowly scoped AODV correctness/safety correction in the separate ns-3 tree, before the A4.2 sweep:

1. In `RouteRequestTimerExpire`, change the terminal retry comparison from equality to `>= m_rreqRetries`, so an over-limit counter is terminal rather than allowing another RREQ retry cycle.
2. In `ScheduleRreqRetry`, compute the full-diameter backoff using a bounded exponent no larger than `m_rreqRetries−1`, with a minimum nonnegative exponent of zero. Preserve the 2.8-s net traversal base and the registered `RreqRetries` value. This prevents undefined signed shifting and ensures the retry delay remains finite and positive if an over-limit state is reached before the timer expires.
3. No other AODV, OLSR, instrumentation, queueing, topology, traffic, or ns-3 source behavior may be changed. Retain the diagnostic source/binary, save the exact source diff, build a distinct executable/library identity, and hash the resulting source and executable before the pilot.

Authorize exactly one new once-only AODV φ10 N=162 runtime pilot in a fresh output directory, same graph/probe/flow seed/routing seed/traffic and simulator settings as repair-v1, but using the corrected simulator. It is a new authorized replacement measurement, not a retry or reclassification. Timeout 3,600 s; serial; MemAvailable ≥8 GiB; swap used 0; no retry. Success is required for a finite projection; failure/interruption keeps A4.2 blocked. Count the pilot whether it succeeds or fails. Current cumulative Alpha accounting is 74/300 (six new attempts beyond the original 70); this addendum adds at most one, for 75/300 before any A4.2 runs.

The corrected AODV implementation is the declared simulator version for all AODV variants in the ensuing A4.2 sweep, if the pilot succeeds and the frozen ≤24 h projection passes. OLSR source/behavior remains unchanged. Disclose this repair and its routing-semantic scope in the A4.2 report; preserve every historical failure and successful OLSR pilot. The projection formula and 24-hour threshold do not change. If successful endpoints from original A4.0A/repair-v1 plus this corrected AODV pilot produce a complete ≤24 h projection, proceed with all original 90 cells under their frozen settings, order, guards, timeout, no-retry and report-only readiness/PDR rules. Otherwise stop before the sweep. No A4.3 work is authorized.
