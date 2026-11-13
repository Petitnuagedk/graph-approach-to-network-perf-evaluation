# Alpha A4.0b — offline diagnosis (stop before A4.1)

**Written after A4.0 results.** Scope: saved-artifact analysis only; zero protocol variants. A4 preregistration and all A4.0 raw outputs remain unchanged. See [Alpha limitations](../../LIMITATIONS.md).

## Disposition

- A4.0B V1 is **PASS for OLSR, AODV, DSDV** under exact timestamp-based identity; V2 and V3 remain PASS for all three.
- A4.0A: three pilot failures are assertion-class crashes (OLSR φ1/φ10; AODV φ10). This leaves required Part-A inputs incomplete; corrected 4.2 wall-time projection is **not estimable**. DSDV φ10 independently triggers the frozen per-node fallback.
- No A4.1 or other simulator variant ran. **Stop here; user authorization required.**

## V1 clause replay (unchanged thresholds)

| Protocol | Tx uniquely assigned / offered | Rx / path checks | Delivered + undelivered forward events = node counters | V1 |
|---|---:|---:|---:|---|
| OLSR | 4,371 / 4,371 | 4,181; all paths valid | 15,326 + 8 = 15,334 | PASS |
| AODV | 4,371 / 4,371 | 4,355; all paths valid | 15,975 + 50 = 16,025 | PASS |
| DSDV | 4,371 / 4,371 | 4,335; all paths valid | 18,279 + 41 = 18,320 | PASS |

Tx sequence is global; RX/forward sequence is per-flow. The offline analyzer assigns Tx by a unique exact scheduled timestamp (0.16384 s interval), joins Rx by that Tx timestamp, and checks forward endpoint pairs. RX and all forwarding rows agree on per-flow sequence at each timestamp (zero inconsistencies). Every delivered packet has consecutive A1 edges and exactly hops−1 counted forwarders; unique deliveries match per-flow totals; every forward event maps and counters conserve exactly. The original failed validator reason (`TX packet cannot be assigned ... 3@0.433333333`) is a sequence-convention defect, not evidence of invalid paths or forwarding counters. Original [validation_4.0.json](../validation_4.0.json) is preserved.

V2: all raw/classified PHY counts and control-parser totals agree; retry callbacks are at least terminal/MAC/queue drops for all protocols. V3: all three flows per protocol have delivered ≤ offered and finite median ≤ p95 delay.

## Pilot failures and saturation

- OLSR φ1 and φ10: OLSR `MessageHeader::Deserialize` assertion at +10.720175795 s / +10.762525735 s; stack enters `ControlMessageKind` → `RecordControlTx`. Both had instrumentation on, forward log off, route dump off. Telemetry-parser involvement is strongly indicated; exact invalid packet/root cause is unknown.
- AODV φ10: negative-delay assertion in `ScheduleRreqRetry` at +24.000100000 s. Separate protocol timer path; cause of negative value is unknown.
- Child SIGABRT −6 propagates through the wrapper as shell status 250. These are not timeouts; crash elapsed time is not a completed-run runtime.
- DSDV φ10 background median PDR = 0.0235947 and max-degree retry ratio = 0.8059319; both frozen saturation triggers fire, selecting per-node load.
- OLSR/AODV φ10 valid runtime inputs are missing. Earlier derived 4.2 estimates used failed runs and are invalid; do not use them.

## Convergence replay

Original detector replay matches stored A4.0B values exactly: OLSR 238.980381135 s; AODV 238.980381192 s; DSDV 238.980380856 s. Each final-five window pattern is fail/pass/pass/pass/pass; each has zero unreceived probe Tx in the last 10 s and zero Rx after the 239 s stop. Total unreceived by stop is 67/9/12, respectively, but none is a final-10-second candidate in flight. The observed tail-effect hypothesis is **not supported**; no detector correction or threshold change is adopted. A delay+interval-truncated sensitivity is ~238.81654 s and is not official. Offline fixtures matching the immediate/delayed/never T3 expectations pass; the tail synthetic shows possibility only. A4.0A has no saved packet timing logs for replay.

## Rerun proposal only

1. One OLSR N=162 φ1% diagnostic canary with instrumentation off, `dumpRoutes=false`: **1 variant**, ≤1 h under the registered per-run ceiling. Compare with preserved instrumented failure.
2. After source review/fix approval and a pre-edit snapshot, retry the three exact failed pilot cells once: **3 variants**, ≤3 h under registered per-run ceilings. Actual runtime unknown; no unchanged-config rerun recommended.

Combined ceiling: **4 variants / 4 h**. No canary or rerun was launched. Current accounting remains A4 9 attempts and cumulative Alpha 21/300; the planned A4 remainder is 252, leaving 27 cap units outside the plan (not authorization).

## Artifacts

Analyzer and detailed CSV/JSON results, synthetic tests, exact read-only input hashes, and output manifest are in this directory. See [INPUTS.sha256](INPUTS.sha256) and [MANIFEST.sha256](MANIFEST.sha256). Amendment: [A4 amendment 1](../amendment_1.md). Budget was re-read and already records 9 attempts / 21 total, so it was not changed.
