# A4.1c preregistration — offline detector validity and event audit

**Registered before inspecting any A4.1 run log or per-run packet/flow output.** Scope: offline only, 0 variants, no ns-3 invocation, no simulator, no reruns, no detector change, no cell disposition except the user-directed DSDV protocol drop recorded as a decision (not a routing finding). Do not modify A4.0*/A4.1/A4.1b artifacts, preregistrations, or amendments. Write only within this stage plus one A4.1c entry in `alpha/gates.md`. Budget remains 70/300. Retained protocols for future Alpha design: AODV and OLSR. DSDV is out of scope; Phase 6D's DSDV outage question is not tested in Alpha. Record the requested literal rationale placeholder: “user-directed drop, rationale: [user to state]”.

## Source-defined units and frozen inputs

G0 reads `alpha/A4/a4.py` source only. `FRAME_RATE = 1.0` frame/s, so one frame is 1.0 s. PASS only if the report cites this source fact. No frame/warm-up values will be recomputed in A4.1c.

Use the 45 A4.1 packet logs, run ledger and `derived_4.1_runs.csv` read-only; use the existing A4.1b per-run table solely for the preregistered G8 membership comparison. Probe matching is by unique `app_tx_time_s` on the frozen 0.1-s initial Tx and 0.16384-s packet interval (1024 bytes at 50,000 bit/s), not global callback sequence. Reception latency is `event_time_s - matched app_tx_time_s`. Count unique matched delivered probe packets in chronological Tx schedule order.

The known A4.1b AODV-cluster membership comparison (G8) is the exact run-ID set recorded in its `aodv_113s_cluster.csv`; compute membership independently as AODV runs with first delivery in [100,110] s over all 45 A4.1 runs, then compare exact sets and report any differences. This is a membership audit, not a causal or protocol verdict. Analyze only AODV/OLSR (30 runs) for G4/G5/G7/G9; inspect the 45-run ledger/log membership for G8 only.

## Frozen gates

- **G4 window-dominance:** among AODV/OLSR runs with recomputed maximum delivered-probe gap ≤1.0 s, calculate readiness minus first-delivery offset. PASS iff at least 80% lie inclusively in [9.0,10.0] s. Also report how many of the eligible runs have absolute readiness ≤10.5 s. Report offset distribution by protocol × N (n, min, median, max and count in interval); no reclassification threshold changes after inspecting results.
- **G5 first-five latency:** for every AODV/OLSR run, calculate latency for each of its first five unique matched receptions. PASS iff every one of these latencies is ≤100 s and all 30 runs have five such receptions. Separately report exact G8 cluster-membership agreement, including the N=92 WS AODV member if present; do not conflate that set comparison with a per-packet latency.
- **G7 OLSR event structure:** fixed pair is BA OLSR N=92 and BA OLSR N=162. For each, find the longest interval between consecutive unique matched probe Rx times. Report interval endpoints/duration; whether any scheduled probe Tx after the gap end has a matched Rx after that end; count unique Rx in `[gap_end, gap_end+1.0)` s. Compare equal-duration windows: the gap interval, the immediately preceding interval of the same length (clipped only if it precedes time zero, with actual duration reported), and the immediately following interval of the same length. Report scheduled Tx, unique Rx, and loss counts in each. Descriptive only; no causal attribution.
- **G9 OLSR warm-up validity:** each OLSR protocol × N warm-up is valid only if G0 and G4 pass and none of its five contributing runs is censored (>180 s or NaN readiness). If either detector gate fails, use `invalid_pending_detector`; if gates pass but a run is censored, use `not_derivable_censored`; otherwise `valid`. For AODV, report its A4.1b reconciliation status without relabeling it as a new G9 pass. Do not calculate/recommend a warm-up value.

G6 (DSDV alignment) is removed from gating and no DSDV timing analysis is in scope. All thresholds are fixed. Any additional diagnostic is explicitly labeled **“written after A4.1c results”** and remains descriptive.

## Classification, options, and budget

Classify the detector as measuring **convergence**, **window-fill**, or **indeterminate**, using only G0/G4/G5: if G0/G5 fail, or evidence does not discriminate, classify indeterminate; if G0 and G5 pass and G4 passes, classify window-fill; if G0 and G5 pass and G4 fails, classify convergence. State the operational rule and do not recompute warm-up or propose another detector.

List proposal-only 4.2 policies, choosing none: (a) keep A4.1 AODV values and treat all OLSR warm-up as unresolved; (b) fixed warm-up selected from noncensored observations only (no value selected here); (c) readiness-gated per-run 120-s measured window; (d) drop OLSR N=92/162 cells as a separate future decision. For each give frame-seconds/run-length implication and variant costs without running simulations. Use the given design sizes: 4.2 = 90 variants, 4.3 = 48; budget spent 70/300. Full design leaves 92 budget units. Dropping two OLSR sizes removes 30 4.2 and 16 4.3 variants; retention or warm-up-policy alternatives add 0 variants. State which future counts are conditional on G4/G9, and that alternatives are not selected.

## Outputs and stop

Produce CSVs for all 30 AODV/OLSR per-run data (first delivery, first-five latency values, readiness, offset, maximum gap, censor status, G4 eligibility, G8 membership) and separately for G7 per-window/event details and G4 distribution/G8 membership results. Report all gate verdicts, per-run table, G7 evidence limits, OLSR/AODV warm-up status, options, budget, and at most five decisions; report ≤150 lines. `run.sh` invokes Python analysis only. Create one manifest after final outputs; include this frozen preregistration and stage artifacts. Append exactly one A4.1c gate entry including the user-directed DSDV drop placeholder. Stop; no A4.2/A4.3, reruns, detector changes, or further cell dispositions.
