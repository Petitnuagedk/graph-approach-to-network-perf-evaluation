# A4.0d readiness candidate — frozen before recomputation

**Frozen 2026-10-13, before the reportable recomputation.** Existing detector outputs under A4_0c are immutable and remain separate. An exploratory implementation check (before this freeze) found the otherwise matching immediate T3 could qualify at 9 s due to the one-second leading-edge allowance; the reportable frozen rule below additionally requires 10 s elapsed since first scheduled Tx. The earlier check is not reportable validation evidence.

## Candidate definition

- Use only unique delivered probe Rx timestamps, matched to scheduled probe packets by the deterministic flow schedule; duplicate Rx does not add a delivery. Let $G=1.0$ s and the existing trailing horizon be 10.0 s.
- Evaluate at each unique Rx event time $t$, no earlier than 10 s after the first scheduled Tx. In the closed trailing interval $[t-10,t]$, consider the leading distance from $t-10$ to the first Rx in that interval and every completed adjacent-Rx inter-delivery interval. A window is ready iff it contains delivered packets and every such *completed* interval is at most $G$; the first Rx may be exactly one $G$ after the left boundary. Return the earliest Rx event that begins the final contiguous suffix of ready windows. A window with an over-$G$ gap fails. If no ready suffix exists, return NaN.
- An outstanding Tx without an Rx is not declared lost or converted into a gap; only completed delivery intervals are tested. Do not use the simulation-stop tail as a loss. This is the in-flight exclusion. It does not alter the original/C95/C90 definitions.
- Candidate choice is fixed: keep $G=1.0$ s and the 10-s trailing horizon if (i) all three frozen T3 expected outcomes are exactly 10 s / 24 s / NaN and (ii) inserting zero through three isolated single-packet losses into the continuous synthetic probe schedule leaves readiness exactly unchanged. Otherwise mark the candidate failed and do not tune it after seeing validation results.

## Fixture rules

T3 uses 1-s packet schedules from 0 through 40 s: immediate delivery of all packets; delayed delivery only from 15 through 40 s; and never-stable delivery on alternating packets only. For the inserted-loss test, use the A4 probe interval $\Delta=0.16384$ s, deliver a continuous schedule for at least 40 s, then remove 0, 1, 2, or 3 isolated packet deliveries at indices separated by at least 5 packets; use event time equal to scheduled time to isolate the packet-loss effect. The baseline and all four variants must yield identical readiness. These tests are descriptive validation of this candidate, not protocol variants.

## Reporting rule

Report readiness beside original, corrected-original, C95 and C90 using the saved A4.0B per-packet logs. C95 is not adopted for warm-up. Apply the preregistered censor rule to the *candidate* only: readiness >180 s or NaN makes that validation observation censored; actual 4.1 warm-up remains not derivable if any of the five family-r1 runs for that protocol,N is censored. For an uncensored single validation observation, display the mechanical 1.5× ceiling whole-frame value as a diagnostic only; it is not a substitute for five-family 4.1 results. Flag a value determined by one delivery outage.
