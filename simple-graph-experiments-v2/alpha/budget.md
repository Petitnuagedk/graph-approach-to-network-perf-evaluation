# Alpha protocol-variant budget

## Tango campaign — 2026-10-21

Tango was stopped before generation by the preregistered swap guard (`/swap.img` configured/active, although unused). No ns-3, graph-run, or protocol variant was launched. Variants spent: **0**; total unchanged.

## A3 registration

- Frozen cap: **12 protocol variants** total for A3.
- Counting unit: one protocol × one registered workload × one instrumentation-option state executed in ns-3. Repeated seed/config execution would consume another variant and is disallowed unless preregistered; A3 permits no retries.
- Planned allocation: T1 all-up path, OLSR and AODV with instrumentation enabled and `flowFraction=0` = 2 variants; T4 Phase 1 static-warm0, three protocols with A3 flags off plus the same three with instrumentation on and `flowFraction=0` = 6 variants. Total planned: **8/12**. Four remain unspent and are not authorization for additional runs.
- T2 flow-selection/static-distance checks and T3 synthetic convergence checks are offline tests, not protocol variants. Compilation and test execution do not count as protocol variants.
- Static routing and DSDV variants are excluded. Do not run a performance sweep, extra protocol, seed, flow fraction, or A4 pilot under this budget.
- Update the executed count only after each registered T1/T4 protocol run, and preserve failed/interrupted attempts in the denominator.

### A3 execution accounting

- Executed/attempted: **8/12** (T1 OLSR/AODV 2; T4 three protocols with flags off and the same three with instrumentation plus `flowFraction=0`, 6). No retries or substitutions. Four cap units remain unused and are not authorization for more runs.
- T1 recorded all 391/391 offered/delivered probe packets for both protocols. OLSR node-forward counts were 0/391/391/0; AODV counts were 2/391/391/0, so the AODV endpoint-zero and exact forwarded-total checks failed by two events.
- T4 flags-off and instrumentation-on outputs matched each other after removing only the timing columns. Both failed the strict frozen Phase 1 reference comparison because the reference has 18 total columns (16 non-timing) while the current source writer emits 62 total columns (60 non-timing). No columns were dropped to force compatibility.
- Budget is closed at 8/12. Do not spend the remaining four units in this A3 registration.

## A3b corrective registration

- Single preregistration: `alpha/A3b/prereg.md`, final SHA-256 `c056faa6df3037213efe3be1cf8d4a3fecbfab04af116604823ad3b7ca43193c`. This is a separately authorized, post-result corrective block; it does not revise A3's original FAIL.
- Maximum and exact plan: **4 variants** — T1 OLSR and AODV (instrumentation + flowFraction=0, opt-in event log), and T4 B0-trace OLSR/AODV flags off. Each once, no retry/substitution. No static route, DSDV, same-trace flags-on T4, or A4.
- Executed/attempted: **4/4**; total Alpha A3+A3b authorization **12/12**. T1 OLSR/AODV each delivered 391/391 with corrected node counts 0/391/391/0 and total 782. T4 B0 OLSR/AODV both matched their golden rows on every non-time field. Offline diagnosis/T2/T3 and builds cost 0 protocol variants. No retries/substitutions; A3b is closed.
- Same-trace T4 flags-off versus instrumentation-on equality was excluded as preregistered; A3's old outputs use a different trace. Do not start A4 or any extra protocol variant.

## A4 registration (before any A4 run)

- Single preregistration: `alpha/A4/prereg.md`, SHA-256 `159c1d0a96cf99adec47ead45df186d34706a6fc6b0c2f5a6f36d47bc6f23cc8`. The A4 cap is 300 total Alpha protocol variants; A3/A3b consumed 12 before A4.
- Planned maximum: A4.0 9 + A4.1 45 + A4.2 135 + A4.3 72 = **261 A4 variants**, running planned total **273/300**. These are ceilings; failed/interrupted attempts count, preregistered skips do not. Update this section after every A4 batch and preserve actual attempted/skipped counts.
- Optional φ=2% A4.2 runs cost up to 15 per size and are charged first against the A4.3 72-variant allowance. Replication cuts follow the preregistered order (r3 before r2; only sizes requiring φ=2% are reduced before untouched sizes). The global cap is hard: no run if its planned execution would raise attempted plus authorized planned spend above 300; stop and ask first.
- Before every batch exceeding 50 variants, record the preregistered runtime projection and stop if it exceeds 24 h. For A4.2, run cheapest classes first, update after the first 15 variants, and project again before continuing. At registration, no A4 variants had run; live attempt counts are recorded below.

### A4 live execution accounting
- A4 attempted protocol variants: **58**; cumulative Alpha spend: **70/300**.
- 4.0A: 6 attempted; 3 failed/timeout/malformed/unknown.
- 4.0d: 4 attempted; 2 failed/timeout/malformed/unknown.
- 4.0B: 3 attempted; 0 failed/timeout/malformed/unknown.
- 4.1: 45 attempted; 0 failed/timeout/malformed/unknown.
- 4.2: 0 attempted; 0 failed/timeout/malformed/unknown.
- 4.2_phi2: 0 attempted; 0 failed/timeout/malformed/unknown.
- 4.3: 0 attempted; 0 failed/timeout/malformed/unknown.
- 4.3 allowance used: 0 φ=2% charges + 0 replication attempts = 0/72.

### A4.2 repair-v1 additive budget authorization

Registered separately in `A4/A4.2/repair_v1/prereg.md` before any replacement-pilot launch. This preserves the historical 70/300 count and authorizes at most 3 new once-only replacement pilot attempts for missing projection endpoints, then at most the original 90 A4.2 variants if the frozen projection passes. Maximum cumulative charge is 163/300. Failed/interrupted replacements count; no retries or substitutions. At registration, repair-pilot attempts remain 0/3 and A4.2 attempts remain 0/90. No A4.3 variant is authorized.

Repair-v1 outcome: all 3 replacement attempts were charged; the two OLSR replacements succeeded and the AODV φ10 replacement failed (exit 134). One further diagnostic-only AODV φ10 invocation is separately authorized in `A4/A4.2/repair_v1/addendum_2.md`; it will count as one attempt whether it completes or aborts. Current cumulative Alpha spend is 73/300; 0/90 A4.2 sweep attempts. This diagnostic does not authorize a further replacement pilot, A4.2 sweep, or A4.3.
The registered AODV φ10 diagnostic has now started and is charged: cumulative Alpha spend **74/300**. A4.2 sweep remains 0/90; A4.3 remains 0.
Diagnostic result: the AODV φ10 attempt failed (exit 134); operands established counter 32 vs configured retry limit 2 and signed `1 << 31` overflow. A third preregistered repair addendum authorizes a bounded-counter/backoff source correction and one once-only corrected AODV φ10 pilot. If started, that pilot counts as attempt 75, making cumulative spend 75/300; A4.2 and A4.3 remain 0 until separately satisfying the frozen projection gate.
The once-only corrected AODV φ10 replacement pilot has started; charge attempt 75. Cumulative Alpha spend is 75/300. No further diagnostic or replacement is authorized unless separately registered; A4.2/A4.3 remain unstarted.
Corrected AODV φ10 pilot succeeded once (attempt 75). Together with the three repair-v1 pilot attempts and one diagnostic, new repair charges total 5; cumulative prior-to-sweep spend is 75/300. Frozen A4.2 90-cell projection is 17,747.909 s (4.929975 h), below 24 h, so all 90 registered A4.2 attempts are authorized, once each. A4.3 remains unauthorized.
Live A4.2 update: cell 1 (`ba_N42_r1`, AODV φ1) completed successfully; 1/90 A4.2 attempts charged, cumulative Alpha spend 76/300. The serial sweep continues. No A4.3 attempt.
Final A4.2 checkpoint accounting: 60/90 A4.2 attempts, all successful; the frozen 60-run re-projection was 30.926 h (>24 h), so remaining 30 N=162 cells were not attempted. Repair/diagnostic additions charged 5 attempts. Cumulative Alpha spend is **135/300**. A4.2 is incomplete; no A4.3 or further A4.2 attempts without separate user direction and a new registered disposition.

### A4.2 continuation-v2 budget authorization — 2026-10-14

The user's explicit continuation decision authorizes at most the 30 previously unattempted N=162 A4.2 cells once each, reusing the 60 completed cells without reruns. New attempts are charged as launched; failures, timeouts, and interrupted runs count, with no retries. Current spend remains 135/300 before continuation; maximum after all 30 new attempts is 165/300. No A4.3 spend is authorized.

Continuation launcher frozen before execution: [continue_remaining.py](A4/A4.2/repair_v1/continuation_v2/continue_remaining.py), SHA-256 `2757a611c9b54354f5603ba8cb269896760474a2cb0d789cc67a63de22f23e16`; checksum file [RUNNER.sha256](A4/A4.2/repair_v1/continuation_v2/RUNNER.sha256). No continuation run has started.

## Cap amendment (user decision, recorded 2026-10-13)

- Previous Alpha cap for 4.3 : 300 protocol variants.
- New Alpha cap for 4.3 : 310 protocol variants.
- Reason: A4.3 (AODV + OLSR, 5 families x 3 sizes x 2 protocols x 5 loads = 150 variants) cannot fit under 300 after the A4.2 spend of 90 (running total 160 before A4.3).
- Authorized by: user.
- Effect: running total 160 + 150 = 310, which is at the new cap. No further Alpha variants may be added without a new amendment.
- The original cap of 300 remains recorded above; this entry does not replace it.

## A4.5 cap amendment (user decision, recorded 2026-11-12)

- Previous authoritative historical accounting: 335/340 protocol variants.
- A4.5 allocation: 30 protocol variants (five graph families × three sizes × two protocols).
- New Alpha cap: **365 protocol variants**.
- Authorized by: user.
- Effect: 335 prior variants + 30 A4.5 variants = 365/365; A4.5 fits exactly within the amended cap.
- This amendment does not alter the separate 135/300 ledger entry; that discrepancy remains disclosed and must not be silently erased.
