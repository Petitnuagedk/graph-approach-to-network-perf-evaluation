# A4 amendment 3 — written after A4.0d results

**Status:** post-result offline analysis and the two specifically authorized A4.0d attempts. The A4 preregistration and amendments 1–2 are unchanged. A4.0d is closed at 2 variants; cumulative Alpha spend is **23/300**. No A4.1 variant ran.

## 1. A4.0d attempt outcomes

The N=42 OLSR regression (`40D_geodesic_N42_r1_olsr_regression`) completed in 26.114 s, peak RSS 63,080 kB, exit 0. It matched all 52 compared existing non-timing columns; the append-only unparsed packet/byte columns were present and zero; packet, byte, and per-node control totals conserved. This validates the patch on that exact run only.

The N=162 OLSR φ1 canary (`40D_geodesic_N162_r1_olsr_phi1_canary`) ended after 208.941 s with SIGABRT/exit 134, peak RSS 353,688 kB. `simulator.log` records an ns-3 `Buffer::Iterator::PeekU8()` assertion while `Ipv4Header::Deserialize` is called by `TraceIpDropCb` during `Ipv4L3Protocol::HandleFragmentsTimeout`, at simulation time 40.761731766 s. The trace is not in the OLSR `MessageHeader::Deserialize` path addressed by the parser patch. Therefore this outcome neither demonstrates a parser-patch regression nor proves the parser safe for all OLSR traffic; it leaves the exact canary cell unknown and requires separate source review. It is not a performance failure. No retry occurred. The two-consecutive-assertion pause threshold was not reached by this single assertion.

The fixed crash policy for future authorized work is: record simulator assertions as `failed: simulator assertion`, never retry, and pause after two consecutive assertion crashes. A crash/unknown N=162 lowest-load cell blocks a formal five-family protocol-drop verdict; only five valid completed lowest-load failures can support that verdict.

## 2. Readiness detector and DSDV characterization

The reportable implementation follows the frozen `A4_0d/readiness_recompute_plan.md`: unique schedule-matched probe Rx, $G=1$ s, 10-s trailing windows, require at least 10 s since first Tx, and report the start of the final contiguous suffix of ready windows. Frozen T3 and isolated-loss tests pass exactly. Keep C95 **not adopted** for warm-up. Candidate results on A4.0B N=42 are:

| Protocol | Original (s) | Corrected 0.99 (s) | C95, diagnostic (s) | C90 (s) | G=1 readiness (s) | Status |
|---|---:|---:|---:|---:|---:|---|
| OLSR | 238.980381 | 21.404960 | 20.913440 | 20.088480 | 20.581661 | uncensored |
| AODV | 238.980381 | 11.738400 | 11.246880 | 10.913440 | 10.915101 | uncensored |
| DSDV | 238.980381 | 206.216480 | 205.724960 | 16.175773 | 205.393181 | censored >180 s |

Readiness-derived whole-frame ceilings (ceil of 1.5× seconds) are 31 OLSR and 17 AODV frames, diagnostic only. DSDV's 309-frame mechanical value is also diagnostic, not an operational warm-up. The DSDV result is set by the late delivery gap and is censored by the frozen >180-s rule.

DSDV has 12 probe losses, in three four-packet bursts at 0.591520–1.083040, 15.500960–15.992480, and 195.724960–196.216480 s. Largest post-first-delivery gap is 1.322702 s (14.853071167–16.175773079); the late event gap is 1.177191 s. Neither exceeds the preregistered >5-s outage threshold, so neither is comparable to the 15-s Phase 6D outage. Two bursts fall roughly 0.5–0.7 s after 15-s periodic-update ticks, but saved control events are empty; report temporal proximity only, not causation. Global no-route, route-error, and queue-drop counts are zero; all-run PHY Rx drops total 37,293. Counters lack timestamps, so interval-specific changes around 195.7–196.3 s cannot be inferred.

## 3. Parser patch and integrity

Parser fixture tests pass: valid aggregate, malformed first type, truncated packet, non-OLSR UDP, and computed packet/byte classification conservation. The full source passed syntax-only validation and the serial ns-3 build. Pristine source SHA-256: `ef8e5412a23100136449f1b44bbfb18be1575a659c5f1a889be78f0808bdbdb6`; tested/applied source SHA-256: `f6e2f0ce89c19c8af78eb244087bf39b2ce4656a2bab11bf67b440e24b4eda6d`; stored patch SHA-256: `6c70267b6e68857bb65d7fd5744e8daf27cb86d1a4ab918bf3692de7b377dd8e`. Protected ns-3 source is byte-identical to the tested patched copy. Regression observed zero unparsed packets/bytes and conserved counters; canary crashed in the separate IPv4 drop trace before providing parser totals. A4.0c's immutable `INPUTS.sha256` records the pre-patch source hash; its source entry now differs solely because of this separately approved patch. No A4.0c artifact or hash file was edited; the pristine snapshot remains intact.

## 4. Projection and execution limits

Offline projection covers the maximum 252 future variants (45 in 4.1, 135 in 4.2, 72 in 4.3), uses at most four workers, and assumes ideal scaling. The 1.25 multiplier is illustrative; it corresponds to a hypothetical 180-s warm-up in the preregistered 4.2 formula `(warmup_frames+120)/240`, not a universal warm-up. The preregistered preliminary ratio 300/120 gives multiplier 2.5.

At 1.25, ideal k=4 projections are 14.55 h (OLSR AODV-anchor bound) to 15.90 h (OLSR DSDV-anchor bound). At 2.5, the same OLSR bounds are 26.98 h and 29.48 h, exceeding 24 h even under ideal k=4. These are assumption-driven projections, not guarantees; the canary does not calibrate a valid OLSR runtime. If a 24-h total-work ceiling is binding, 4.2/4.3 scope reductions or a separately authorized allocation are needed under multiplier 2.5; k must remain ≤4. Update estimates from valid 4.1 observations before authorizing later batches.

Proposed future hard timeouts, to freeze before 4.1: N=42 1,800 s; N=92 3,600 s; N=162 7,200 s. They are scaled sizing caps, not measured per-size runtimes. Each timeout consumes its attempt; no retries. A4.0d itself used the authorized 3,600-s cap per attempt. Resource guard before launch: block if available RAM <8 GiB or any swap is used. Both actual launches were serial (k=1); host limit is four physical cores and maximum worker count k=4.

## 5. Stop condition

Do not start A4.1 under this amendment. The N=162 canary is an assertion/unknown, not a pass or protocol drop. Its failure is in IPv4 fragment-timeout drop instrumentation, not the OLSR parser guard. Resolve through source review and obtain renewed authorization before any further variant. A single N=162 OLSR geodesic canary, even if it had passed, would only have established viability for that one cell and would not validate OLSR at N=92/162 across graph families.

## 6. Follow-up user direction — 2026-10-13

The readiness candidate is adopted **provisionally for A4.1 only**; it is not committed for A4.2/A4.3. Reassess after acquiring delivery-gap data from more than one network size. C95 remains unadopted for warm-up. The user authorized one bounded N=162 OLSR reproduction diagnostic (0 or 1 variant), with no code changes, to assess whether the assertion recurs beyond the original seed/run. The campaign parallel-worker cap is k=4; the single diagnostic is serial. This does not authorize A4.1. The authorized diagnostic uses the same N=162 workload and flow selection with ns-3 seed 43; its outcome is recorded separately in the A4.0d run ledger and report.

The seed-43 diagnostic reproduced exit 134 at simulation time 40.821537830 s (versus 40.761731766 s for seed 42), after 211.870 s wall time and 354,652 kB peak RSS. It hit the same `Buffer::Iterator::PeekU8` → `Ipv4Header::Deserialize` → `TraceIpDropCb` → `Ipv4L3Protocol::HandleFragmentsTimeout` path. Source SHA-256 remained `f6e2f0ce89c19c8af78eb244087bf39b2ce4656a2bab11bf67b440e24b4eda6d`; no code changed. Recurrence across two seeds makes an original-seed-only explanation less likely. Since both runs are the same N=162 trace/workload and there was no controlled size comparison, the result does not establish that the assertion is unique to N=162. The canary and reproduction are two consecutive assertion crashes, so the pause policy is active: no more variants without renewed authorization. The assertion is not performance evidence; the unknown N=162 low-load cell continues to block a formal five-family drop verdict.

## 8. Post-fix validation and A4.1 authorization — 2026-10-13

The one explicitly authorized post-fix N=162 OLSR seed-43 replay completed 120 frames with exit 0 after 741.120 s process wall time and 231,520 kB peak RSS. The repaired `TraceIpDropCb` did not assert; this verifies the callback fix for this workload only and is not protocol-performance evidence. Probe delivery was 632/726; the run reported 2,056 unparsed control packets / 4,712,352 bytes. Aggregate, classified, and per-node control counters each conserved at 31,016 packets / 21,406,256 bytes. No retry occurred. The replay and fix validation do not erase the prior unknown A4.0d canary outcome.

After the post-fix replay completed, the user explicitly authorized the registered A4.1 stage. The current stage run must attempt the 45 planned family × size × protocol variants once each, with k≤4 (the runner executes serially), a 3,600-s per-run cap, and the ≥8-GiB available-memory / zero-swap launch guard. Use the adopted G=1 s, trailing-10-s readiness detector from unique, schedule-matched packet logs for A4.1 convergence and warm-up; do not substitute the older built-in convergence field. The readiness candidate remains provisional for A4.1 only and must be reconsidered after gap results span more than one size before any later-stage decision. This authorization does not include A4.2 or A4.3; no retries or other variants are permitted.

For A4.1, `a4.py` was updated to calculate that candidate detector from packet logs, and to enforce/log the per-run RAM/swap guard and count the separate A4.0d ledger in live budget refresh. This differs from the original pre-run runner identity (`1377cece…`); the active A4.1 process uses SHA-256 `e842079d3365d8b1cfc39dcb725420bfa4d47908ea43211c5c6aaecd73ea6499`. The A4.1 packet schedule match was checked against the three prior A4.0B logs, reproducing readiness values 20.581661135 s (OLSR), 10.915101192 s (AODV), and 205.393180816 s (DSDV). The protected fixed simulator source and built executable identities at stage start were `9745439728fd4c5ca5f8667c90abb596e5c6746a81b21b9260d0904f0b63a433` and `4a39073b4b2b1ede65b35452717acf231c664a89db256fed194f8f0b448de74c`; no source edits are planned in A4.1.

## 7. Drop-callback repair and bounded validation

The ns-3 call sites show the `Drop` callback's packet is already the IPv4 payload; the callback receives the decoded `Ipv4Header` separately. `HandleFragmentsTimeout` passes a partial reassembly payload. The bug was `TraceIpDropCb` calling `PeekHeader(Ipv4Header)` on those payload bytes. The source fix removes that reparse, skips application classification except for no-route/route-error reasons, checks payload length before peeking UDP, and uses the supplied IP header's protocol. Offline self-tests cover app UDP attribution, other UDP port, non-UDP, truncated UDP, and partial fragment-timeout payload. Full source syntax validation, serial ns-3 build, and the offline helper suite pass; no protocol variant was used for these checks.

The existing `A4_0d/graph-run.patched.cc` is the pre-fix source snapshot, SHA-256 `f6e2f0ce89c19c8af78eb244087bf39b2ce4656a2bab11bf67b440e24b4eda6d`. Fixed protected source SHA-256 is `9745439728fd4c5ca5f8667c90abb596e5c6746a81b21b9260d0904f0b63a433`; rebuilt executable SHA-256 is `4a39073b4b2b1ede65b35452717acf231c664a89db256fed194f8f0b448de74c`. In response to the user's explicit repair request, exactly one post-fix seed-43 N=162 replay was launched with a 3,600-s cap; outcome pending. No other variant or A4.1 run is authorized.

## 9. A4.1 completion and offline gap correction — 2026-10-13

The later, explicit A4.1 authorization was executed to completion: 45/45 registered variants succeeded once, serially, with no retries, failures, assertions, or timeouts. This supersedes the earlier pending wording only as to the post-fix replay and A4.1 execution status; it does not authorize A4.2/A4.3 and does not clear the original A4.0 failures.

Post-run review found the A4.1 gap helper incorrectly treating global Tx callback sequence values as per-flow packet indices. All 45 packet logs were corrected offline by joining unique app-Tx schedule timestamps to Rx timestamps; all logs passed schedule checks with zero duplicate, unmatched, or off-schedule rows. Original and corrected gap values plus interval endpoints are retained in [the recomputation audit](all_up_gap_recompute.csv); the offline implementation is [recompute_4_1_delivery_gaps.py](recompute_4_1_delivery_gaps.py). No simulator was rerun. Corrected DSDV maxima at N=42/92/162 are 1.271390/1.995780/5.326506 s. RGG N=162 DSDV exceeds the frozen strict 5-s cutoff and is excluded from later load/replication metrics; no DSDV gap reaches 15 s. BA N=162 OLSR has a 23.578562-s gap, showing delivery-gap behavior is heterogeneous across sizes and protocols. Reconsider the provisional readiness detector before any later-stage proposal; no later-stage work is authorized. Full results and derived warm-up/censoring records are in [A4.1 report](A4_1_report.md).
