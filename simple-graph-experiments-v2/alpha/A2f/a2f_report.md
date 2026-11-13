# Alpha A2f final report — timer-scale boundary, U/K interface, and MPC diagnosis

**Status: A2f deliverables complete.** A2f-1 through A2f-3 passed their registered gates. A2f-4 completed its registered offline diagnosis and sweep, with an overall frozen classification of mixed/inconclusive. This report closes only A2f; it does not authorize A3, Beta execution, ns-3, protocol variants, upstream source changes, or an MPC implementation change.

## A2f-1 — exact-quota structural boundary

**Gate: PASS.** The feasible exact-quota run counts for a nontrivial schedule are integers $1\le K\le\min(U,D+1)$, where $U=\operatorname{round}(F\cdot life)$ and $D=F-U$. Thus mean up-run duration belongs to the discrete set $\{U/K\}$, not a continuous interval. All 27 `(F,life)` cells, 432 timer/fps `rho` rows, formula identities, and 3 hand checks passed. Timer ratios are dimensional comparisons, not protocol predictions. Exact endpoints, timers, and unreachable targets are in [A2f-1 result](A2f-1/result.md).

| Evidence | Result |
|---|---:|
| Boundary cells | 27/27 |
| Timer-ratio rows | 432 |
| Formula identities | All pass |
| Hand checks | 3/3 pass |

**Limitations for this section:** life and mean up-run remain confounded under the A2a stability rule; timeline diversity is family-independent by construction; the generator is patched and non-upstream; the A2b gate is non-binding by greedy max-min construction; Level 2 route diversity is tie-break-sensitive; time-respecting reachability permits waiting and is not an OLSR/AODV/DSDV oracle. A sampling-frequency axis is recommended to interpret timer-to-frame reachability, not as a protocol-performance claim.

## A2f-2 — isolated `uk` timeline interface

**Gate: PASS after registered correction.** The opt-in `uk` adapter provides explicit exact U/K requests and typed infeasibility without clamping; legacy and patched behavior remain separately available. The original life=.7/K=16 cell was an arithmetic deviation from the preregistered midpoint K=11; it is retained but excluded. A preregistered replacement at K=11 passed. Final 12-cell grid: 2,400 exact U/K traces, all per-cell Monte Carlo p-values at least .01 where informative, 2 one-category p-values explicitly uninformative; all 28 infeasibility checks returned the exact typed fields; regression checks passed 15/15 each across legacy-vs-original, patched-v2-vs-original, patched-v2-vs-stored A2c, and `uk`-vs-patched-v2. Details and hashes are in [A2f-2 result](A2f-2/result.md).

**Limitations for this section:** life and mean up-run remain confounded under the A2a stability rule; timeline diversity is family-independent by construction; the generator is patched and non-upstream; the A2b gate is non-binding by greedy max-min construction; Level 2 route diversity is tie-break-sensitive; time-respecting reachability permits waiting and is not an OLSR/AODV/DSDV oracle. `uk` decouples the interface; it does not expand the finite exact-quota support or establish protocol behavior.

## A2f-3 — generator-only life/run-duration decoupling

**Gate: PASS.** 300/300 registered operations completed; all requested/realized U/K and instantaneous S–R masks matched, life error was zero, shortcut fraction zero, and assembled edges remained within their skeletons. Average-tie Spearman on the 12 unique design centers was -0.09909 (absolute value <=.30); the A2a comparator was +1.0. Temporal reachability is store-carry-forward and descriptive only. Full tables and provenance are in [A2f-3 result](A2f-3/result.md).

**Limitations for this section:** life and mean up-run remain confounded under the A2a stability rule; timeline diversity is family-independent by construction; the generator is patched and non-upstream; the A2b gate is non-binding by greedy max-min construction; Level 2 route diversity is tie-break-sensitive; time-respecting reachability permits waiting and is not an OLSR/AODV/DSDV oracle. The decoupling result does not imply randomized routing-protocol availability.

## A2f-4 — offline MPC multi-pair diagnosis

**Execution complete; outcome mixed/inconclusive.** The corrected read-only census covered all 18 A2d item2 correction-v1 cells. All had exact F=120/U=60; MPC up-run counts (2 or 3) are descriptive because its legacy MPC timeline uses a separate exponential-run process and does not enforce A2a's exact K. This was clarified in registered [A2f-4 addendum 1](A2f-4/prereg_addendum_1.md) before accepting cause labels and before the new sweep. The preliminary K=30 audit is preserved as exploratory and superseded.

The ordered census labels were: 6 requested joint-state absences, 3 requested-state under-supply cases, and 9 cells with no observed fidelity failure. Shared-source pairs passed 42/42; disjoint pairs passed 3/42 (m=2: 1/6, m=4: 2/12, m=8: 0/24). The single `disjoint_m2_seed11` example had all-down `00` requested 60 times but only 3 `00` pool frames; requested states were not absent. It realized 00:3, 01:49, 10:8, 11:60 and had 57 selected-pool status substitutions. This exemplifies under-supply and assembly mismatch in the saved outputs, not proof of a specific internal fallback branch.

All 45 preregistered disjoint m=2 sweep operations succeeded under their 60-second/no-retry limits; maximum wall time was 8.3312 s and all frame edges stayed in the fixed ER skeleton. Per-pair fidelity passed 53/90 overall: 30/30 at `p_edge=.3`, 13/30 at `.5`, and 10/30 at `.7`. At `.3`, all three pool sizes were already operationally resolved, so the strict registered capacity-transition classifier labels that stratum inconclusive. At `.5`, no operation was supply-ready even with 30,000 pool frames, though the `00` pool count rose from 14/300 to 208/300 across the five-seed aggregate; no status was absent. At `.7`, the requested `00` state had zero pool frames in all 15 operations and remained absent at 10,000 and 30,000; this is registered persistent-absence evidence under these samples, not mathematical impossibility. The overall classification is mixed/inconclusive because only one of three strata receives a named class. No MPC change was implemented.

The proposal is fail-closed exact-status assembly: raise typed insufficiency metadata when a requested joint state has fewer unused frames than demand, rather than silently selecting a Hamming-nearest state. Expected effect: no status substitutions in successfully assembled frames, while shortfall becomes an explicit operation failure; it does not create missing support or guarantee fidelity. Proposal only; no implementation authorized. The full audit, per-seed data, classification, proposal, and 420-entry artifact manifest are in [A2f-4 result](A2f-4/result.md).

**Limitations for this section:** life and mean up-run remain confounded under the A2a stability rule; timeline diversity is family-independent by construction; the generator is patched and non-upstream; the A2b gate is non-binding by greedy max-min construction; Level 2 route diversity is tie-break-sensitive; time-respecting reachability permits waiting and is not an OLSR/AODV/DSDV oracle. In addition, saved artifacts do not expose same-status PID-filter relaxation, and observed associations do not prove internal causal mechanisms.

## A2f artifacts and provenance

- Gate log: [alpha/gates.md](../gates.md), including preregistration hashes, addendum, stage results, and A2f-4 disposition.
- A2f-1 preregistration SHA-256 `c5ffa38a11d4c0c85601dd9fb1a4db1066866df89e52128fc5ce9fa5264d7b9e`; calculation script `3a6b720ccebe7dd74eacc1df422bebadd9dc295444ad1951afef3dd4cb1d7825`; boundary table `a9317ef2c23a85f3615083114e6a47f1cff0b9cfb80e69412c47c97fe1ae8549`; rho table `1c0a5f73f67f2ab65df4f557646d853f7508466e80a86da12ba479e441f964f6`; summary `79e123a004bd9376acf96fb5eb8d1b061fcc7405a370526283684a79d6b846e2`; narrative result `9e5edad2a1c98d10f720da90550e65a8963111380948060754a7f14090cbe468`.
- A2f-2 preregistration SHA-256 `e5ee3ffb00d07ade1550cece56484b56432f6d864ca02533965a9f11e47c06e9`; corrected replacement runner `93aae030255b5844ae0d758763da5ac1b6d622dfc18cd1e164748781b2789a75`; corrected summary `e0f52c089e7b78ed8818de497e8fbae79f224ab2c9140cf8edf7601e6466f192`; corrected per-seed file `86a5ca0520295a7e898aef781287335db792afafae622f27e75dfc956578fac9`; narrative result `4bba9514cda7b201bf4b0078d58627578f484ee7c066bb528df74f73d6f36e0b`; final result details and source/overlay hashes are in [A2f-2 result](A2f-2/result.md).
- A2f-3 preregistration SHA-256 `b423370340c38840d403941a86f46dc9f78dbd8064bcff76c3928a86b8f4b477`; runner `438f7c7e5ebfb19d39b5cfa7f317d80065c2c92824829c68db04dcfbd8c69ceb`; summary `d4e8542298c94bc616bbe5b201f630220c2144c917214c281179726dfe08592e`; Spearman `f4668402262ac25069c3eaed3ad37d230de5f1fba45f1cc242542771882465e9`; per-trace CSV `3e45e6709e0d391568de846198600f063f2c90a154935128d4e821fab7fb86f3`; cell summary `0fc66c78931f6f4795ad8109272092fe018cf4618b57bc7b86c46a838f4f6643`; 2,104-artifact manifest `66308402630b8f1d25f6741dc920a301fd9642ea0aa472115a5fc14e5ed4bead`; narrative result `6f597db381d4b94e43fb77ce9c70f043f83f058196651893b7ea2e645536aa28`.
- A2f-4 base preregistration SHA-256 `931253195e235a56bfb2c9adcfa6c8ac60f6598e0d919cf4df7e5b82b5f4ab65`; addendum `874117c922abcd4d42c6d0568a9fd5bfb8a27667d2696f9a3407dd370df6fa5a`; result report `b6e463aca0ffb859f4c46ce5aa9d23ec2c0c8884c160824e5b58cfea154267f3`; 420-entry manifest `1e40f83ab27f45d90fa6a926e57b9ca6bdd60bb7f4e5fd85167a8520259c3d8f`.

All new A2f work remained generator-only: 0 protocol variants, no ns-3. The A2f-4 preliminary quota interpretation, the A2f-2 arithmetic deviation, and the initial A2d item2 helper/serialization failure remain disclosed rather than erased.

## Decisions requested

1. **Mandatory fps axis for A3/Beta:** recommend **yes**. Preserve frame-rate metadata alongside life and U/K so timer-to-frame feasibility is explicit; the ratios do not predict protocol performance.
2. **Adopt the `uk` interface for Beta:** recommend **yes**, as an opt-in exact-quota interface with typed infeasibility and no implicit clamping; preserve legacy compatibility where required.
3. **Implement the proposed MPC fix:** recommend **no, not yet**. Keep the fail-closed policy proposal-only until a separate preregistration authorizes a falsification test; do not confuse explicit shortfall reporting with improved capability.
4. **Authorize A3:** **no authorization is granted by this report.** A3 requires a separate explicit user decision and scope review.
