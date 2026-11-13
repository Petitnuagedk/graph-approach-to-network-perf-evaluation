# Beta campaign transition: SPC to MPC

**Decision date:** 2026-11-13  
**Decision:** significant design change recorded by user  
**Execution status:** SPC execution cancelled

## Decision

The Beta campaign will no longer use SPC as its operative dynamic-graph construction for protocol measurements. The campaign is being redesigned around MPC, with the MPC construction explicitly entangled with the source–destination pairs that generate the protocol traffic.

The required relationship is:

1. freeze or deterministically generate the complete traffic-pair set induced by the registered `phi` rule;
2. pass that same pair set into the MPC generator/characterization;
3. impose and measure the registered dynamic parameters on those traffic pairs, rather than only on the A1 probe pair;
4. record per-pair realized life, stability, persistency, feasibility, and path identity before interpreting protocol metrics.

The probe pair may remain a separately reported diagnostic if retained, but it is no longer sufficient as the sole pair on which the dynamic constraints are defined.

## Cancellation

All active SPC B3 processes were terminated on 2026-11-13. Verification found no remaining B3 runner or ns-3 `graph-run` process.

The active SPC B3 run was interrupted after a partial set of rows had completed. Its outputs remain in the B3 directory for auditability only. They are not MPC results, are not pooled with the future campaign, and must not be used for Beta conclusions under the revised design.

The earlier SPC one-row validation and any completed SPC B3 rows are likewise retained as historical execution artifacts, not accepted evidence for the revised MPC campaign.

## Gate consequences

- **B0:** SPC-specific characterization is superseded. B0 must be re-registered for MPC pair-aware construction, pair-set provenance, per-pair feasibility, and per-pair realized metrics.
- **B1:** SPC harness equivalence does not establish MPC equivalence. B1 must be repeated against the A4.5 static reference using the revised MPC-aware traffic construction.
- **B2:** SPC generator characterization does not validate MPC. B2 must be repeated with the same traffic-pair set that will be used by protocol runs and must report pair-aware life/stability/persistency behavior.
- **B3:** The SPC B3 block is cancelled and does not advance the Beta gate. A new MPC B3 preregistration, ledger, smoke test, and authorization are required.
- **B4/B5/full sweep:** remain stopped.

No existing SPC result is silently relabeled as MPC. No code was changed as part of this transition record.

## Required MPC re-registration items

The replacement preregistration must specify:

- exact MPC API/build identity and provenance;
- exact traffic-pair generation rule, including `phi`, flow seed, probe designation, and whether the probe is included in the constrained pair set;
- whether the pair set is generated once and reused across axes/seeds or regenerated per row;
- the definition of pair-level path life, stability, and persistency;
- joint feasibility rules and treatment of infeasible pair/cell combinations;
- per-pair realized metrics and aggregate reporting rules;
- static A4.5 reference handling;
- memory/swap guard, worker limit, stop boundary, and revised protocol-variant accounting.
