# Alpha A4.0c — detector, OLSR parser, projection

**Written after A4.0b results. Offline only: 0 variants; cumulative spend remains 21/300. Stop before 4.1.** A4.0, A4.0b, both amendments and the protected simulator file were not edited.

## Gate table

| Check | Result | Gate/disposition |
|---|---|---|
| Step 1 V1 negative control | Corrupted one counted forward event in a copy per protocol; path clause fails 3/3 | PASS sensitivity check |
| Step 2 original detector | Exact replay matches three saved validation values; final Rx boundary artifact established | Diagnosis complete; new definition needs approval |
| Step 2 candidate C95 | Passes immediate/delayed/never T3, in-flight tail, and single random-loss fixture | Candidate only; not adopted for 4.1 |
| Step 3 parser copy | Malformed aggregate reproduces SIGABRT; valid aggregate does not; patched copy syntax-check passes | Patch prepared; actual crash root cause not proven |
| Step 3 4.2 projection | 14.61–16.11 serial h under stated load-slope model | Below 24 h in projection; 4.1 and worker overhead excluded |
| Step 4 canary | One patched OLSR N=162 φ1 variant proposed; not run | Needs explicit authorization |

## Detector

Candidate definitions/selection rule were frozen before the reportable final recomputation in [recompute plan](detector_recompute_plan.md); first exploratory output is preserved separately. Δ = 0.16384 s. Corrected-original excludes Tx younger than Δ but retains the 0.99/10-s suffix rule. C95/C90 use the same maturity rule at 0.95/0.90; the predeclared strictest-passing rule selects C95. At ~61 Tx/10 s, 0.99 permits **zero** losses: 60/61 = .9836. One random MAC loss therefore resets the original gate.

| Run | Original s | Corrected .99 s | C95 s | C90 s | Last probe loss Tx s | Last failing eval / in-flight |
|---|---:|---:|---:|---:|---:|---|
| N42 OLSR validation | 238.980381135 | 21.404960 | 20.913440 | 20.088480 | 11.404960 | 238.978720 / 1 |
| N42 AODV validation | 238.980381192 | 11.738400 | 11.246880 | 10.913440 | 1.738400 | 238.978720 / 1 |
| N42 DSDV validation | 238.980380856 | 206.216480 | 205.724960 | 16.175773 | 196.216480 | 238.978720 / 1 |
| N162 AODV φ1 pilot | 118.888217284 | unavailable | unavailable | unavailable | unavailable | no packet log |
| N162 DSDV φ1 pilot | 118.887355714 | unavailable | unavailable | unavailable | unavailable | no packet log |
| N162 DSDV φ10 pilot | NaN | unavailable | unavailable | unavailable | unavailable | no packet log |

For each validation run, last Tx = 238.978720000 s; its Rx delay is OLSR .001661135, AODV .001661192, DSDV .001660856 s. `convergence − (last Tx + delay)` is exactly 0 at CSV precision. Pilot last scheduled Tx is 118.884000000 s; finite saved values minus that time are .004217284/.003355714 s, **implied only**—no saved last-Rx timestamp to verify the delays. DSDV φ10 is NaN, so the identity is undefined.

Original last-ten evaluations are dumped in [detector_last10_original.csv](detector_last10_original.csv) (time, event type, numerator, denominator, ratio, pass/fail); all failing evaluations and their in-flight counts are in [detector_all_failures.csv](detector_all_failures.csv). Each validation run has two failures in its final ten evaluations; each is a Tx event at 238.814880 and 238.978720, ratio 61/62, one packet in flight. Following last-loss+10 s, 1,338/1,388/203 Tx evaluations still fail—exactly one just-emitted packet is counted before its Rx. Intervening Rx/expiry evaluations pass. The C++ detector matches its written event-time rule; it does not mature/correlate packets. Original convergence is consequently the final packet's Rx boundary here, not evidence that the route first became ready then. Pilot last-loss/window evidence is unavailable because Part A saved no packet times.

C95 returns 10/24/NaN s on T3; 10 s on the in-flight-tail case; and 10 s on the single random loss at ~61 packets/10 s. It is not the final Rx time in either added case or in any of the three validation-run recomputations; pilot C95 is unavailable rather than imputed. C95 is selected by the frozen rule, but remains a proposal pending approval. See [synthetic results](detector_synthetic_tests.csv) and [six-run comparison](detector_comparison_six_runs.csv).

## OLSR parser diagnosis (6 lines)

- `RecordControlTx` sends every non-app IPv4 Tx to `ControlMessageKind`.
- Under OLSR, it parses UDP payload as OLSR without checking UDP port 698 or packet length.
- `PeekHeader(MessageHeader)` asserts unless the assumed first-message type byte is 1–4.
- The code peeks only the first message; a valid two-message aggregate did not assert in the unit test.
- A malformed two-message fixture (first type 0, second valid TC) reproduced the exact SIGABRT; actual run packet bytes were not captured.
- [Prepared patch](olsr_parser_fix.patch) is only against [pristine copy](graph-run.pre_edit.cc); [patched copy](graph-run.patched.cc) passed C++20 syntax-only check. Protected source remains unchanged.

Hashes: pristine copy `ef8e5412a23100136449f1b44bbfb18be1575a659c5f1a889be78f0808bdbdb6`; patched copy `f8cc8259ebca2e4dd2195f287c00ecbb7cf2ea582eeb76abb910c90847776e3d`; patch `01475cf68e3370ade73b8ff7507d7be53fd605afcc15cbe553ce2d111dad9785`. The [unit test](olsr_parser_unit_test.cc) passed: valid aggregate no assert; malformed first type legacy SIGABRT; raw guard rejects safely. Its [build command](olsr_parser_test_build.txt) and [result](olsr_parser_unit_test_result.txt) are recorded. This reproduces the assertion condition, not proof of the actual A4.0 packet's cause.

## 4.2 projection

Background counts are `llround(κN)`; conservative warmup = 180 s and time multiplier = `(180+120)/240 = 1.25`. Anchors: valid AODV φ1 662.069 s and DSDV φ1 869.165 s at 130 background flows; DSDV φ10 2,284.325 s at 1,304 flows. Assumed DSDV slope = 1.205418 s/background flow, extrapolated to other protocols as a load-slope assumption. Scale by `(N/162)^2`; five families per N, three roles/protocol, 135 cells total. Does not include 4.1, parallel overhead, or family-specific variation.

| N | κ=.25 | κ=.5 | κ=1 |
|---:|---:|---:|---:|
| 42 | 11 | 21 | 42 |
| 92 | 23 | 46 | 92 |
| 162 | 41 | 81 | 162 |

| 4.2 case | Serial h | k=1 | k=2 | k=4 | k=8 | vs 24 h |
|---|---:|---:|---:|---:|---:|---|
| AODV | 4.371 | 4.371 | 2.186 | 1.093 | .546 | under |
| DSDV | 5.870 | 5.870 | 2.935 | 1.468 | .734 | under |
| OLSR (AODV–DSDV bounds) | 4.371–5.870 | 4.371–5.870 | 2.186–2.935 | 1.093–1.468 | .546–.734 | under |
| All protocols | 14.613–16.112 | 14.613–16.112 | 7.306–8.056 | 3.653–4.028 | 1.827–2.014 | under |

Worker times are ideal serial-total/k, not machine-specific forecasts. Detailed per-cell calculations are in [projection_by_cell.csv](projection_by_cell.csv); no core count is assumed.

## Proposal and decisions needed — no execution

1. Select/approve detector definition: C95 proposed; original and corrected-original results remain reported separately.
2. Approve or reject applying [prepared parser patch](olsr_parser_fix.patch) to the protected `graph-run.cc`; it has not been applied.
3. Provide available CPU core/worker count and parallel policy; state whether the actual 4.1+4.2 design must shrink after a measured projection. Current 4.2 estimates alone are under 24 h.
4. Approve/revise proposed crash-cell rule: `failed: simulator assertion`, exact cause recorded, not a performance failure, no retry; an unknown N=162 lowest-load cell blocks the all-five-family protocol-drop verdict.
5. Authorize or decline exactly one OLSR N=162 φ1 patched-parser canary (`instrumentation=true`, `a3bForwardLog=false`, `dumpRoutes=false`; ≤1 h hard timeout). Do not rerun OLSR/AODV per-pair φ10. If run, 1 variant; projected cumulative spend 22/300, leaving 26 of the 27 outside-plan cap units. Declining leaves real OLSR parser behavior/runtime untested and its 4.2 projection only bounded.

No canary, rerun, or A4.1 variant was executed. Verify outputs using [MANIFEST.sha256](MANIFEST.sha256); read-only provenance inputs are in [INPUTS.sha256](INPUTS.sha256). See [Alpha limitations](../../LIMITATIONS.md).