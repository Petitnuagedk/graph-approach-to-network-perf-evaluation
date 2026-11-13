# Beta gate log

## Revised-scope correction — 2026-10-13

**DOCUMENTATION ONLY.** [Beta charter](Beta.md) now supersedes A4.4 as the baseline reference: Beta will vary stability, persistency, and path life with YaDyGaGa on the pending A4.5 static all-links-up baseline. Scope remains AODV and OLSR at N=42/92/162; DSDV and adversity remain excluded/deferred. A4.4 is retained only as historical dynamic frame replay. No B0/B1 or other Beta run was performed.

## Beta charter registration — 2026-11-12

**REGISTERED — NO RUNS.** [Beta charter](Beta.md) was updated to register the B0–B5 subfolder layout and hashed before any Beta execution. SHA-256: `2896cbd19a7991701a52099939fe173630c1d669bb59bbb45e4fcbde852ba1ff`.

The charter fixes the research question, static A4.4 baseline, network-size and dynamic-axis definitions, path-life/stability/persistency support limits, $K\le D+1$ feasibility rule, level and seed policies, 500-variant user cap, stage order B0–B5, gates, descriptive attribution, plotting, limitations, and open decisions. It explicitly excludes DSDV, random-link fraction/lifetime, constrained-path count, and adversity until validated. The running Alpha ledger 335/340 is not charged to Beta.

No B1 harness check, axis characterization, generator run, ns-3 run, sweep, or adversity work was performed. No Alpha artifact, preregistration, `budget.md`, or A4.4 record was edited. [Registration report](report.md) lists the written sections and unresolved unknowns.

## Canonical-root merge record — 2026-11-12

The root `beta/` directory is canonical. The Alpha staging contents were merged without overwriting existing root files or deleting the staging directory. The merged B0 feasibility and provenance records are now under [B0](B0/), and B1 remains blocked. No Beta execution occurred.

## Execution amendment — 2026-11-13

The preceding preparation status is historical. A4.5 is complete with 30/30 successful static runs, the user raised the cap to 1,200, and B1 was explicitly authorized. Only B1 is covered by this authorization; later Beta stages remain gated.
