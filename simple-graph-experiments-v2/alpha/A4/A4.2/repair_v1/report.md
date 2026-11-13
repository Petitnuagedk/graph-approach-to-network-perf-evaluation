# A4.2 repair-v1 — stopped at preregistered 60-run projection checkpoint

**A4.2 is incomplete and closed at the frozen checkpoint stop.** The user requested completion of A4.2, but the preregistered rule explicitly requires stopping when a corrected total exceeds 24 h. Do not describe 60/90 as complete or start A4.3.

Addendum 1 SHA-256 `5d203dc1f1201f2d5f06512d1653d6eb2ba3a77cb6226f6af35eaf378ce3058e`; addendum 3 (AODV correction) SHA-256 `9f0ee2c3a57ef40444dcd73d0a0a72e04ed0d5e65c5b529e1d2d5f1d181b1a46`.

**Initial gate:** frozen successful-pilot projection 4.930 h; passed the registered ≤24 h gate. **Checkpoint after 60:** actual serial wall time 12.472 h; median actual/projected correction 4.8184; updated total 30.926 h >24 h. Frozen instruction: stop. The remaining 30 runs were not launched.

**Attempts and budget:** 60/90 A4.2 cells attempted; 60 successful, 0 unsuccessful; cumulative Alpha charge 135/300. The five authorized repair/diagnostic attempts are separately recorded. No retries or substitutions.

All 60 A4.2 runs that started completed successfully. Fully observed registered grids: N=42 and N=92 (30/30 cells each). N=162: 0/30 attempted. Exact plan states and reason: [planned_cells.csv](planned_cells.csv). Per-run data: [per_run.csv](per_run.csv); per-flow post-readiness records: [per_flow_post_readiness.csv](per_flow_post_readiness.csv).

Readiness flags among the 60 completed runs: 60/60. Detailed protocol×N×load counts, using the preregistered five-family denominator: [miss_table.csv](miss_table.csv). Completed-size status matrix and unattempted N=162 cells: [status_matrix.csv](status_matrix.csv).

Per-cell highest passing loads and common candidates are summarized in [operating_candidates.csv](operating_candidates.csv). N=42 and N=92 cover their full registered grid; N=162 has no measured candidate. No 2% loads or other replacements were run.

Interpretation is limited to the two completed network sizes and tested A1 realization. The 30 N=162 cells are unknown/not attempted, not failures. Since this stage stopped at the frozen projection rule, no further continuation is authorized by this report.

The repeated AODV failure was diagnosed as signed `1 << 31` overflow at RREQ count 32 with configured retry limit 2. The bounded backoff / terminal `>=` correction is recorded in [AODV correction note](aodv_retry_correction.md), applied to all AODV sweep runs, and source/library hashes are in [pre-run identities](PRE_RUN_IDENTITY.md). OLSR source was unchanged. Historical failed pilot attempts remain failed.

**STOP. No A4.3, no more A4.2 variants, no detector/warm-up changes, no DSDV reinstatement. A separate user decision and registered continuation would be required to exceed the frozen 24-hour stop rule.**
