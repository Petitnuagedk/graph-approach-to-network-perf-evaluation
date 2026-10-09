# Phase 7 protocol-variant budget log

Hard cap: **300 protocol variants for Phase 7 only**. Accounting unit for this Phase 7 log: graph-run invocations × routing variants in each invocation. Offline audits and code-only checks that do not invoke graph-run consume 0 protocol variants. This Phase 7 ceiling does not by itself set a separate Alpha/Beta cap or its numeric value. Any simulator batch must be preregistered first, counted before launch, and this log updated immediately after the batch.

| Stage / batch | Graph-run invocations | Routing variants per invocation | Protocol variants consumed | Cumulative total | Status |
|---|---:|---:|---:|---:|---|
| 7A read-only integrity audit | 0 | 0 | 0 | 0 | Complete; no simulation |
| 7B-B0 legacy golden (2026-10-08) | 1 | 3 (OLSR, AODV, static) | 3 | 3 | Qualifies: 60 source frame matrices + ceil(45 s × 1 fps) = 105 applied frames; existing run reused, no rerun |
| 7D v2 generator offline acceptance | 0 | 0 | 0 | 3 | Complete; 195 offline traces, 39/39 cells passed; no graph-run invocation |
| 7D H4 ±1 s and ladder provenance audits | 0 | 0 | 0 | 3 | Complete; stored Phase 6 data only, no simulation |
| 7B-B1 no-interpolation channel and all-up controls (2026-10-08) | 5 | 1 (static) | 5 | 8 | All 5 completed; all-up controls pass, down-loss equivalence/zero down deliveries pass, but static PDR differs from usable uptime by 0.2419 in each synthetic run (limit 0.05); B1 gate fails |
| 7B-B1′ post-B1 deadline-qualified offline analysis | 0 | 0 | 0 | 8 | Exploratory saved-data calculation only; frozen τ=50 ms and absolute tolerance 0.05; all 3 original runs pass offline but do not count as confirmation |
| 7B-B1′ fresh confirmation (2026-10-08) | 3 | 1 (static) | 3 | 11 | All 3 pass the separately preregistered deadline-qualified criterion; original B1 aggregate-PDR failure remains unchanged |
| 7D generator redesign validation rerun (offline, 2026-10-08) | 0 | 0 | 0 | 11 | 39/39 cells, 195 traces; passed concurrently with B2 and rerun after review with the same result |
| 7B-B2 legacy regression (2026-10-08) | 1 | 3 (OLSR, AODV, static) | 3 | 14 | **Executed before the timing probe.** Pass: all 15 deterministic event/route/oracle/diagnostic files byte-identical; result CSV identical excluding only wall/CPU columns; trace/settings/frame accounting match. See [B2 invocation record](7B/B2_invocation_record.json) and [comparison](7B/B2_comparison.json). |
| 7D minimal-scale timing smoke test (2026-10-08) | 1 | 1 (static) | 1 | 15 | One static-only run on 5 nodes and one flow, `dumpRoutes=true`; 60 source frames + 45 warm-up = 105 applied. ns-3 wall 0.227225 s, CPU 0.227203 s; process 1.385584 s; explicit build check 0.60 s. Not a scale projection. See [timing summary](7D/timing_probe/timing_summary.json). |

**Spent: 15/300. Unspent: 285.** The arithmetic is 11 after B1′, plus 3 for the executed-and-passed B2 regression = 14, then plus 1 for the subsequent timing probe = 15. B2's resolved config timestamp (1791468154) precedes the probe config timestamp (1791468440). Original B1's aggregate-PDR/usable-uptime gate remains failed; B1′ and B2 passed their separate criteria. Generator redesign validation passed offline at zero variants. The timing probe does not authorize 7C or a campaign. Beta's cap-counting unit is now specified separately as protocol variants; its numeric cap remains to be preregistered.
