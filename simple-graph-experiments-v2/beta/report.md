# Beta charter registration report

Date: 2026-11-12

Written [Beta.md](Beta.md) with these sections:

1. Research question and scope.
2. Baseline definition and all 30 A4.4 family/protocol statuses.
3. Baseline interpretation and convergence-affected rule.
4. Dynamic axes, API parameters, source references, A0-R2/A2 support, coupling, and feasibility.
5. Level and seed policies.
6. Budget, cap source, Alpha ledger treatment, and per-stage accounting.
7. Rough wall-time estimate and user-termination policy.
8. B0–B5 stage order and gates.
9. Pass criterion and attribution.
10. Reporting and plot requirements.
11. Limitations.
12. Open user decisions.

Unknowns not resolved from Alpha records: the final numeric below/above levels for each axis, the validated adversity definition/API parameter, and any B0 build or pair-definition details not present in the A4.4 configuration records. These are intentionally left for B0 or a later adversity preregistration.

No experiment, B1 rerun, sweep, generator run, ns-3 run, or adversity work was performed. No Alpha artifact, preregistration, budget file, or A4.4 record was edited.

Registered SHA-256 of [Beta.md](Beta.md): `2896cbd19a7991701a52099939fe173630c1d669bb59bbb45e4fcbde852ba1ff`.

The parent directory now contains [B0](B0/), [B1](B1/), [B2](B2/), [B3](B3/), [B4](B4/), and [B5](B5/). Each stage README defines the artifacts that must remain inside that stage folder.

## Merge addendum

The canonical Beta tree is the parent `beta/` directory. Preparation artifacts previously staged under `alpha/beta/` were merged into the root using a non-destructive copy. Existing root artifacts were preserved; no files were deleted. The staging directory remains available for audit comparison.

The merged preparation records supersede the earlier A4.4 operational wording: A4.5 is the intended static reference, B1 is blocked by the incomplete A4.5 result, and the 600-variant Phase 1 design conflicts with the recorded 500-variant cap. No Beta run was launched.

## Execution amendment — 2026-11-13

The preceding statement is historical. A4.5 is complete with 30/30 successful static runs and supplies the N=42 seed-42 AODV/OLSR references. The user raised the cap to 1,200; Phase 1's 600 variants are within the amended cap, while Phase 2 remains beyond it. B1 was explicitly authorized and is the only Beta stage launched under this amendment.
