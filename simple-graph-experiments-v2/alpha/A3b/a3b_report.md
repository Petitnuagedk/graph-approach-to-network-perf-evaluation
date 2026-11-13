# Alpha A3b — corrective instrumentation validation

**Result: PASS on the preregistered amended gates.** This post-result corrective stage is separate from A3: the original A3 FAIL remains unchanged in `alpha/gates.md`. No A4/pilot was run. See [Alpha limitations](../LIMITATIONS.md).

## Registration and provenance

Single preregistration: [prereg.md](prereg.md), final SHA-256 `c056faa6df3037213efe3be1cf8d4a3fecbfab04af116604823ad3b7ca43193c`. Step 0 preceded all A3b edits: [source_before.cc](source_before.cc) and target both hashed `0f04a8d87fd261a6544fb76ce5d6e80fa8f4154cdb7aebfd4632b17cd0da4d84`. Final target SHA-256: `ef8e5412a23100136449f1b44bbfb18be1575a659c5f1a889be78f0808bdbdb6`; exact unified diff: [source.patch](source.patch), SHA-256 `0de19f34754f0f66005909edd0528fe73622cd752844a7cde2d8a25dee5639c8`. Rebuild passed. Commands are frozen in [run.sh](run.sh). The B0 historical source itself is unavailable; its recorded graph-run hash is retained in the preregistration.

## Step 1 diagnosis (saved evidence, then instrumented follow-up)

Saved A3 records alone made H_a/H_b/H_c undecidable; [offline diagnosis](diagnosis.md) retains that conclusion. Opt-in A3b events resolve the two extras as **H_a supported**: both are at node 0, source `10.1.0.1` (node 0's own), sequences 0 and 1, and both timestamps are 30.367396832 s, exactly when node 0 receives the first AODV RREP. Source code routes unknown destinations through tagged loopback and later invokes the queued forward callback on route resolution. These events coincide with RREP reception rather than preceding it. **H_b not supported:** zero AODV RERRs were logged and the two events coincide with initial resolution. **H_c not supported** for these events.

## Gate table

| Gate | Threshold | Observed | Verdict |
|---|---|---|---|
| T1 OLSR | 391/391 delivered; node forwards 0/391/391/0; total 782 | 391/391; 0/391/391/0; 782; per-packet path reconstruction matches | PASS |
| T1 AODV | Same fixed thresholds; protocol-neutral local-address predicate | 391/391; 0/391/391/0; 782; old source-local events excluded; paths match | PASS |
| T2 flow selection/distances | Unchanged A3 offline checks; all 13,041 unique unordered pairs | Selection/reverse-direction checks pass; NetworkX verifies 13,041/13,041 | PASS |
| T3 convergence | Immediate 10 s; delayed 24 s; never-converging NaN | 10 s; 24 s; NaN | PASS |
| T4 B0 OLSR | Match each B0 row on every non-time column | 60/60 columns match, same order | PASS |
| T4 B0 AODV | Match each B0 row on every non-time column | 60/60 columns match, same order | PASS |
| Source provenance | Exact post-edit source hash and unified diff present | Both present and inventoried | PASS |
| Variant accounting | Exactly four, once each | 4/4 A3b; 12/12 including A3 | PASS |

## New-column classification

| Current-only columns versus B0 | Classification | Reason |
|---|---|---|
| None (current and B0 schemas are the same 62 columns) | N/A | A3/A3b diagnostics remain in separate opt-in CSVs; no new result columns were introduced. |

T4 compares each protocol row to its matching B0 row, after removing only `wall_time_s` and `cpu_time_s`. The same-trace flags-off versus instrumentation-on comparison was excluded: A3's existing outputs use another trace, and the required flags-on B0 run would be a fifth variant. No equality claim is made for that comparison.

## Deviations and decisions

Exactly four protocol variants ran once: T1 OLSR/AODV with instrumentation and event logs; T4 B0 OLSR/AODV flags off. No static-route variant or DSDV rerun; no retry/substitution. Phase 1 is retired as the golden because the Phase 2 denominator differs (PDR 1.000→0.822; app-Tx 296→360); this changes the gate reference, not measurement code. The B0 CSV/trace/config remain read-only. A3 remains a historical FAIL.

**Decision 1 — A3 disposition:** recommend accepting A3 as passed only on A3b's amended gates: T1 and B0-based T4 pass and the exact diff is stored. This does not erase A3's original FAIL entry.

**Decision 2 — A4 prompt:** authorization is still needed to write (not execute) the A4 prompt covering N=162 pilot at $\phi=1\%$ and $10\%$, load per pair versus per node, 7C/static status, and the chain-sampler region from A2h. A3b stops here; no A4/pilot is authorized or started.

Per-variant CSV and detailed acceptance data are [variant_results.csv](variant_results.csv), [a3b_summary.json](a3b_summary.json), and [packet_hop_reconstruction.csv](packet_hop_reconstruction.csv). The final [MANIFEST.sha256](MANIFEST.sha256) covers stage artifacts and read-only references; its self-hash is necessarily excluded.
