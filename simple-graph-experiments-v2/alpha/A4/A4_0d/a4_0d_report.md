# Alpha A4.0d — detector, patch, projection, canary

**Status:** A4.0d is closed at its four recorded attempts. Its single post-fix verification replay exited 0 without the fragment-timeout assertion (741.12 s wall; 231,520 kB peak RSS); this is callback-fix validation only, not protocol-performance evidence. The user subsequently authorized A4.1, which has since completed all 45 registered variants. Current accounting is 58 A4 attempts and **70/300** cumulative Alpha variants. No A4.2/A4.3 work is authorized; see the later [A4.1 report](../A4_1_report.md).

## Gates and authorized variants

| Gate/run | Result | Evidence |
|---|---|---|
| Frozen readiness synthetics | PASS | T3 10/24/NaN and 0–3 isolated losses exact |
| OLSR parser fixtures/build | PASS | malformed/truncated classified unparsed; source syntax + serial build pass |
| N=42 OLSR regression | PASS | 52 non-timing fields match; unparsed packet/byte counts zero; sums conserved |
| N=162 OLSR φ1 canary | ASSERTION / UNKNOWN | exit 134 at 40.761732 s; 208.941 s wall; 353,688 kB peak RSS |
| N=162 OLSR seed-43 reproduction | ASSERTION / REPRODUCED | exit 134 at 40.821538 s; 211.870 s wall; 354,652 kB peak RSS; no source changes |
| N=162 OLSR seed-43 post-fix replay | PASS: callback assertion absent | exit 0; 741.120 s wall; 231,520 kB peak RSS; 632/726 probe packets; no retry |

The two pre-fix N=162 runs failed in the same `Buffer::Iterator::PeekU8` → `Ipv4Header::Deserialize` → `TraceIpDropCb` path during `HandleFragmentsTimeout`, not the OLSR `MessageHeader::Deserialize` parser path. The seed-43 reproduction reached the assertion at 40.821537830 s versus 40.761731766 s at seed 42. Recurrence at a second seed makes a one-seed-only explanation less likely, but this does not prove an N=162-only effect: both runs use the same N=162 trace/workload, with no controlled same-seed size comparison. The post-fix seed-43 replay completed 120 frames with exit 0 and no assertion; this validates that the repaired callback avoided that crash on this workload only. The run also reported 2,056 unparsed control packets / 4,712,352 bytes, while total, classified, and per-node control counters each conserved at 31,016 packets / 21,406,256 bytes. Its PDR is not used as protocol-performance evidence. The original two crashes are not performance failures and do not establish parser safety. The unknown N=162 low-load cell still blocks a formal five-family protocol-drop verdict.

Root cause: ns-3's Drop trace passes the IPv4 payload in `packet`, while separately supplying the decoded `ipHeader`. On fragment timeout, `packet` can be only a partial reassembly payload. `TraceIpDropCb` incorrectly attempted to `PeekHeader(Ipv4Header)` from those payload bytes, producing the bounds assertion. The callback now uses the supplied IP header and reads only a size-checked UDP header for `DROP_NO_ROUTE`/`DROP_ROUTE_ERROR`; fragment-timeout and other drop reasons are not parsed for app-port attribution. Offline cases pass for app UDP, non-app UDP, non-UDP, truncated UDP, and partial fragment-timeout payloads. Source syntax, serial build, and the offline self-tests pass.

## Readiness candidate (G=1 s, 10-s window)

The A4.0d candidate rule (pre-specified for this offline recomputation) uses unique schedule-matched probe Rx, minimum 10-s observation age, and the first event in the final contiguous suffix of ready windows. All exact synthetic cases pass. Per the subsequent user decision, adopt it **provisionally for 4.1 only**; do not commit it for 4.2/4.3. Re-examine after obtaining gap data from more than one network size. **C95 is not adopted for warm-up.**

| Protocol | Original s | Corrected .99 s | C95 diagnostic s | C90 s | Readiness s | Gate |
|---|---:|---:|---:|---:|---:|---|
| OLSR | 238.980381 | 21.404960 | 20.913440 | 20.088480 | 20.581661 | uncensored |
| AODV | 238.980381 | 11.738400 | 11.246880 | 10.913440 | 10.915101 | uncensored |
| DSDV | 238.980381 | 206.216480 | 205.724960 | 16.175773 | 205.393181 | censored >180 s |

Mechanical 1.5× frame ceilings: OLSR 31, AODV 17; diagnostics only. DSDV 309 is censored and not an operational warm-up. DSDV has three four-packet loss bursts (0.592–1.083, 15.501–15.992, 195.725–196.216 s); largest Rx gap 1.323 s. None exceeds the preregistered 5-s outage threshold. Timing near 15-s DSDV periodic ticks is not causal evidence; control events are not timestamped. All-run no-route, route-error, queue-drop counters are zero; PHY Rx drops=37,293, with no interval timestamps.

## Patch and integrity

C++ fixtures pass valid aggregate, malformed type, truncated packet, non-OLSR UDP and computed packet/byte conservation. Pristine / patched / patch SHA-256: `ef8e5412a23100136449f1b44bbfb18be1575a659c5f1a889be78f0808bdbdb6` / `f6e2f0ce89c19c8af78eb244087bf39b2ce4656a2bab11bf67b440e24b4eda6d` / `6c70267b6e68857bb65d7fd5744e8daf27cb86d1a4ab918bf3692de7b377dd8e`. Protected source equals tested copy. Regression maintained existing columns and conserved control counters.

## Projection, caps, and decision gate

| Assumption | OLSR lower bound | OLSR upper bound | Ideal k=4 |
|---|---:|---:|---:|
| 1.25 duration multiplier (illustrative) | 58.20 serial h | 63.59 serial h | 14.55–15.90 h |
| 2.5 preregistered 300/120 ratio | 107.93 serial h | 117.92 serial h | 26.98–29.48 h |

Projection spans 4.1–4.3 maximum 252 variants, is ideal scaling only, and does not provide guarantees. 1.25 corresponds only to an illustrative 180-s warm-up. At the conservative 2.5 factor, OLSR exceeds 24 h even at k=4; any binding 24-h total ceiling therefore needs separately authorized scope reductions in 4.2/4.3 or another explicit allocation. Campaign cap is k=4. Proposed future hard caps: N=42 1,800 s; N=92 3,600 s; N=162 7,200 s; freeze before 4.1. Timeout counts, no retry. Launch only with ≥8 GiB available RAM and zero swap used. All original and follow-up A4.0d attempts are serial, k=1.

**A4.1 authorization:** after the single post-fix replay completed, the user explicitly authorized A4.1. The runner derives convergence/warm-up from the adopted provisional G=1 s, trailing-10 s readiness detector using packet-level logs, not the older built-in convergence value. The preregistered 3,600-s per-run cap remains binding; launches require ≥8 GiB available RAM and zero swap. A4.1 is limited to its 45 registered variants; no retries, A4.2, or A4.3 are authorized. Campaign worker cap is **k=4** (runner currently serial, k=1).

## Current disposition

1. Readiness candidate: provisionally adopted for 4.1 only; re-evaluate after gap observations at more than one size, before any 4.2/4.3 commitment.
2. Diagnostic: the seed-varied reproduction confirmed the same callback assertion. The single post-fix replay exited 0 without it; 2,056 control packets / 4,712,352 bytes remained unparsed even though aggregate/type/node counters conserved.
3. A4.1 subsequently completed 45/45 once. The post-run schedule-matched gap correction revealed multi-size heterogeneity; the readiness candidate remains provisional and must be reconsidered before any later-stage proposal. The full result and offline correction are in [A4.1 report](../A4_1_report.md). No A4.2/A4.3 authorization follows.
4. Parallelism: k=4 campaign cap. Under multiplier 2.5, the estimated total still exceeds 24 ideal hours at k=4; decide 4.2/4.3 scope separately before those stages.
