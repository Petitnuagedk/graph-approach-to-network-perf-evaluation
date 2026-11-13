# Beta campaign charter

**Status:** design and registration only; no Beta experiment is authorized by this document.
**Question:** how do dynamic-graph parameters affect routing behavior on the static baseline?
**Generator:** YaDyGaGa, using the isolated patched copy identified in Alpha A0-R2. **Protocols:** AODV and OLSR only. DSDV is excluded by user direction.

## 1. Research question and scope

Beta varies dynamic-graph parameters while holding the static graph family, size, protocol, channel, traffic, and registered baseline configuration fixed. Results are descriptive and conditional on baseline status; they are not rankings, ceilings, or causal attribution.

In scope are one-axis sweeps of path life, stability, and persistency, with plots showing network behavior as a function of each swept value. Adversity is deferred until it has a definition and validation against measured degradation. Out of scope are DSDV, random-link fraction and lifetime, constrained-path count, and any adversity run before its separate preregistration. The generator is YaDyGaGa; random-link fraction and lifetime are deferred rather than silently replaced.

## 2. Baseline definition

The static baseline is the amended A4.4 all-up run: interpolation OFF, the 7B channel, 802.11g, 20 dBm, 50 kbps, 1024-byte packets, and the fixed measurement window below. Phi values are matched on the forwarded-load proxy only: flows × geodesic mean shortest path / N. They are not matched on flows per node and do not establish equal offered load for every family.

| N | phi | realized flows | warm-up | sim time | window | A4.4 family/protocol status |
|---:|---:|---:|---:|---:|---|---|
| 42 | 0.0500 | 43 | 120 s | 300 s | [120,420] | BA: AODV pass; OLSR fail (probe PDR < .99). ER: AODV fail (probe PDR); OLSR fail (probe PDR). Geodesic: AODV pass; OLSR fail (probe PDR). RGG: AODV pass; OLSR fail (probe PDR). WS: AODV pass; OLSR fail (probe PDR). |
| 92 | 0.0150 | 63 | 180 s | 300 s | [180,480] | BA: AODV fail (probe PDR and background median < .95); OLSR fail (probe PDR and background median). ER: AODV fail (probe PDR); OLSR fail (probe PDR). Geodesic: AODV pass; OLSR fail (probe PDR; readiness flag). RGG: AODV pass; OLSR fail (probe PDR). WS: AODV pass; OLSR fail (probe PDR). |
| 162 | 0.0065 | 85 | 320 s | 300 s | [320,620] | BA: AODV fail (probe PDR and background median); OLSR fail (probe PDR and background median). ER: AODV fail (probe PDR); OLSR fail (probe PDR and background median). Geodesic: AODV pass; OLSR fail (probe PDR). RGG: AODV pass; OLSR fail (probe PDR). WS: AODV fail (probe PDR); OLSR fail (probe PDR and background median). |

The source values and per-run outcomes are the A4.4 amended ledger and [A4.4 report](../../simple-graph-experiments-v2/alpha/A4/A4.4/report.md). A Beta baseline is not silently repaired or reclassified.

## 3. Baseline interpretation rule

Report effects as **within passing baseline** or **relative to failing baseline**. A shortfall in a flagged run is labelled `convergence-affected`; a shortfall in an unflagged run at a swept level that differs from baseline is an `axis-associated candidate`. The readiness flag is reported but is not convergence evidence, given the A4.1b finding. No baseline is dropped or ranked by this charter.

## 4. Dynamic axes and support

| Axis | Definition and API parameter | A0-R2 / A2 support | Coupling and feasibility |
|---|---|---|---|
| Path life | Requested fraction of timeline frames in the up state; `SPCTimelineBlockGenerator.path_life` (`path_life` constructor argument). Source: [timeline generator](../../simple-graph-experiments-v2/alpha/A0R2/YaDyGaGa/yadygaga/timelineBlockGenerator.py#L7-L35). | Usable on the patched copy; A0-R2 fidelity passed. A2 path-life support is inherited from the A0-R2 characterization. | Determines up count $U=\operatorname{round}(Fq)$ and jointly enters $K$. |
| Stability | Controls the requested number of up-runs through `SPCTimelineBlockGenerator.stability`; source formula and legacy cap are shown in [the generator](../../simple-graph-experiments-v2/alpha/A0R2/YaDyGaGa/yadygaga/timelineBlockGenerator.py#L201-L222). | Partly usable: it changes transitions and mean up-run, but exact requests can be infeasible. | Together with path life sets up-run count $K$; require $K\le D+1$. |
| Persistency | Probability of retaining a path ID across adjacent up frames, API parameter `pathPersistency`; source: [path-ID assignment](../../simple-graph-experiments-v2/alpha/A0R2/YaDyGaGa/yadygaga/timelineBlockGenerator.py#L92-L114). | Partly usable: it acts on path IDs and can affect route identity when alternatives exist. A2 support is conditional on skeleton class. | It may be inert on a single-path skeleton even when IDs change; it does not change the Boolean schedule in the tested patched implementation. |
| Adversity | Intended future dynamic degradation axis; no validated definition or YaDyGaGa API parameter exists. | Not defined and not usable. No A2 support claim. | No level is selected here. A separate definition, validation, preregistration, and budget line are required. |

The governing feasibility rule is $K\le D+1$, where $D=F-U$. Levels must also be in the valid parameter range, including [0,1] for the three YaDyGaGa parameters. For example, the tested A0-R2 F=120 region permits all listed stability values for life ≤ .5, stability=.8 for life=.7, and no .9-life cells; Beta must check the exact inequality at every selected level and N. Interpolation is OFF. No level is chosen after results are observed.

## 5. Level, seed, and generator policies

For each of path life, stability, and persistency, B0 fixes one level below and one above the A4.4 baseline per N. The final numeric levels are part of the B0 preregistration and must be inside the feasibility region and valid parameter ranges. B0 must record the baseline values, selected levels, $U,D,K$, and the feasibility calculation before any run. The same one-axis design is not interpreted as evidence that the axes are independent.

Use five seeds per level: 42, 43, 44, 45, 46. Baseline comparison data use seeds 42–46 for every (N, protocol). The seed-42 A4.4 rerun is a harness check, not extra data and is not charged as a new Beta baseline observation.

YaDyGaGa is run from the patched copy with its recorded source identity. The frame interpolation setting remains OFF and every run uses the 7B channel. Two workers are allowed under the A4.0d memory guard: at least 8 GiB `MemAvailable` and zero swap. There are no automatic retries and no timeout; the user terminates runs.

## 6. Budget

The user decision sets a cap of **500 protocol variants**; source: **user decision**. A protocol variant is one graph-run invocation × routing protocol. The running Alpha ledger is 335/340 and is not charged to Beta.

| Block | Per N | Three N values |
|---|---:|---:|
| Path life, stability, persistency: 3 axes × 2 levels × 2 protocols × 5 seeds | 60 | 180 |
| Baseline: 2 protocols × 5 seeds | 10 | 30 |
| **B3/B4 total** | **70** | **210** |
| Adversity | added later as its own budget line | separate preregistration |

Each stage preregistration must contain its own budget line. The 210 planned variants are within the 500 cap. The cap may be adjusted only by an explicit later user decision.

## 7. Wall-time planning estimate

Using A4.4 elapsed times as the rough planning basis, serial wall time is approximately 5 h for N=42, 17 h for N=92, and 49 h for N=162, or approximately 37 h with two workers. This is a rough planning figure, not a gate or a scaling claim. The user terminates runs; no timeout is set.

## 8. Stage order and gates

### B0 — charter and build identity; no runs

Read the A4.4 configurations and record the YaDyGaGa build/source identity, interpolation setting, 7B channel settings, stability and persistency values, path life, pair definition, seeds, and all unknowns. Register the numeric below/above levels and the per-stage budget. B0 launches no generator, simulator, or protocol run.

### B1 — harness equivalence; gate

Rerun seed 42 for N=42 with both AODV and OLSR. Match the configuration hashes, probe PDR, background median, and control totals to A4.4 using the preregistered comparison tolerances. Any mismatch stops Beta; no sweep is launched.

### B2 — axis characterization; gate

On the N=42 skeletons, confirm realized path life, stability, and persistency at every registered level. Check whether persistency changes route-level output on each skeleton. If persistency is inert on a skeleton, report it and drop that axis from B3 for that skeleton; do not replace it post hoc. B2 uses no protocol variants unless separately budgeted in its preregistration.

### B3 — N=42 one-axis sweep; gate to continue

Run the registered 70-variant N=42 block: 60 one-axis variants plus 10 five-seed baseline variants. Stop for user review after the block. Do not start B4 before review and a new authorization or recorded continuation decision.

### B4 — N=92 and N=162 sweeps

Run N=92 and N=162 only after B3 review. Each size has a separate preregistration and budget line. Preserve the same axes, seed policy, window, protocol set, attribution rules, and no-timeout/user-termination rule.

### B5 — adversity

Start only after adversity is defined and validated against measured degradation. Use a separate preregistration, level rule, budget line, and gate. No adversity work is authorized by this charter.

## 9. Pass criterion and attribution

The per-run descriptive pass criterion is probe PDR ≥ .99 and background median per-flow PDR ≥ .95 in the registered window. It is not used to stop a run. A flagged shortfall is `convergence-affected`. An unflagged shortfall at a level that differs from baseline is an `axis-associated candidate`. Control bytes per node rising while PDR falls is a `control-amplified candidate`. Do not assign routing or MAC causes without the per-type breakdown. AODV RERR is reported separately.

## 10. Reporting and plots

For each swept axis, plot the axis value on the x-axis against probe PDR, background median PDR and p10, delay, control bytes per node by type, and MAC and collision values. Use separate AODV and OLSR panels and one curve per N. Every plot states whether its reference is within passing baseline or relative to failing baseline, and identifies flagged shortfalls. Report means with sample SD (`ddof=1`) where summaries are made, plus per-run values. All plots and interpretations are descriptive; no ranking or ceiling language is used.

## 11. Limitations

There is one graph realization and one seed per family-size cell at baseline; swept cells extend to five seeds. Architecture effects are confounded with realization effects. The forwarded-load match holds only for mean load and fails for BA hubs. The readiness detector is not a convergence measure. Persistency may be structurally inert on single-path skeletons. Stability and path life are coupled through $K$, and infeasible requests cannot be silently clamped.

## 12. Open decisions

The user must decide: (1) the adversity definition and validation; (2) whether failing baselines are admitted into the sweep; (3) the N=92 and N=162 go decision after B3 review; and (4) any change to the 500-variant cap. B0 must also resolve and record any build, pair-definition, or configuration unknowns that cannot be established from Alpha records.

## 13. Beta directory layout

All stage work belongs in the corresponding subfolder of this parent directory:

- [B0](B0/): charter, build identity, configuration inventory, and numeric level registration; no runs.
- [B1](B1/): harness-equivalence preregistration, outputs, and gate record.
- [B2](B2/): axis-characterization preregistration, outputs, and gate record.
- [B3](B3/): N=42 sweep preregistration, outputs, and review gate.
- [B4](B4/): separate N=92 and N=162 preregistrations, outputs, and gate records.
- [B5](B5/): adversity definition, validation, preregistration, and later outputs only after approval.

Each stage must keep its preregistration, configuration identity, ledger, outputs, report, and gate record inside its own folder. The root charter is the shared scope document; it does not authorize execution.

**Stop boundary:** this charter does not authorize B1, B2, B3, B4, B5, or any experiment. No Alpha artifact, preregistration, budget file, or A4.4 record is changed by this document.

## Revised scope (recorded 2026-10-13)

This section supersedes the earlier A4.4-baseline definition and any dependent wording above. Beta is now documentation-only at this stage and is redefined to vary stability, persistency, and path life with YaDyGaGa on the A4.5 static baseline. The scope remains AODV and OLSR at N=42, 92, and 162; DSDV remains excluded, and adversity remains deferred. No Beta run, B0/B1 activity, or preregistration is authorized by this correction.

The baseline section above is superseded: the Beta reference is A4.5, not A4.4. The A4.4 results remain a historical dynamic frame-replay record and are not a static or Beta reference. The earlier Beta baseline table and its A4.4-derived interpretation are retained for auditability but must be read as superseded, not as the operative baseline.

## Canonical-root merge record (2026-11-12)

This root-level `beta/` directory is now the canonical Beta location. The former `alpha/beta/` contents were merged non-destructively: files that existed only there were added here, while existing root artifacts were preserved. The former `alpha/beta/` directory has not been deleted.

The operative preparation status is the amended F=300 design: A4.5 is the static reference, life 1.0 is a static-reference row and is not generated, infeasible cells are `infeasible_not_run`, and YaDyGaGa must use the pinned tree with `behavior="patched"`. B1 remains blocked because A4.5 has no completed seed-42 AODV/OLSR result. No Beta run has been launched.

The registered exact design is 600 Phase 1 dynamic variants and 2,400 Phase 2 variants, totaling 3,000. The earlier charter records a 500-variant cap; Phase 1 already exceeds it. This conflict is preserved and execution remains stopped pending an explicit user decision. See [cap stop](cap_stop.md), [Beta plan](plan_beta.md), and [B0 feasibility](B0/feasibility_F300.csv).

## Execution amendment — 2026-11-13

The user explicitly raised the Beta protocol-variant cap from 500 to 1,200. The registered Phase 1 design of 600 variants is therefore within the amended cap; the 2,400-variant Phase 2 design remains beyond the cap and is not authorized by this amendment. The cap change does not silently alter the registered design.

A4.5 is complete: its amended ledger contains 30/30 successful static all-links-up ns-3 invocations, including the N=42 seed-42 geodesic AODV and OLSR reference rows required by B1. The earlier pre-launch failure remains historical and is not the operative A4.5 result. B1 is now the next gate and was explicitly authorized by the user on this date; no B2/B3/B4/B5 or full Beta sweep is authorized by this amendment.

## B1 result — 2026-11-13

B1 passed: both registered N=42 seed-42 harness comparisons, AODV and OLSR, matched the A4.5 static reference exactly on configuration identity, frame hash, PDR values, and control totals. B2 is now the next gated stage. No B2, B3, B4, B5, or full Beta sweep has been authorized or launched.

## B2 result — 2026-11-13

B2 completed with the authorized generator-only scope using the pinned A0-R2 patched YaDyGaGa tree and the A2 frame-pool grid. It produced 1,710 rows across the five N=42 families, with 1,710 feasible rows, no substitutions, no errors, and zero protocol variants charged. Persistency responded at the path-ID level and was not inert. B2 passes its gate; B3 remains stopped pending a new user authorization.
