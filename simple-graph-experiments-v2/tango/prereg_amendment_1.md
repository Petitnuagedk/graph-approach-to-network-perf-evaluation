# Tango amendment 1 — implementation and execution boundary

Registered 2026-10-22 after the draft pilot was stopped and before any valid Tango result is accepted. The draft T1 CSVs and stopped pilot are historical implementation artifacts, not Tango results and not pooled with any future run.

The campaign implementation is isolated under `tango/src/`. Every T1/T3 uk schedule operation now executes in a Linux child process with `nice -n 19`, a 60-second join boundary, and explicit timeout/error propagation. The isolated sampler is `alpha/A2f/A2f-2/source`; no existing Alpha source is modified. A1 edge-list hashes are checked before graph reuse. The new graph seed block is 30,000,000 onward and is disjoint from A1's registered seeds.

This amendment does not relax any numerical gate. It does not authorize protocol variants, ns-3, graph-run, Beta, or A4 work. The full implementation remains subject to the original preregistered requirements: exact T1 support and transition checks; exact A1 family parameters; 30 accepted random realizations per family/N; child timeout/error recording; T3/T4 provenance checks; realization-level bootstrap (10,000, seed 20261021); and exactly ten PNG/PDF figure pairs with plotted-data CSVs.

## Amendment 1b — dynamic persistency grid and figure readability

For the dynamic descriptor follow-up, T3 uses pathPersistency values `{0, 0.25, 0.5, 0.75, 1}` rather than the initial two-value exploratory grid. The N=162 pilot is rerun over all five values before any full campaign run. The three dynamic plots use one panel per family, jittered observations, life-specific colors, and realization-level bootstrap summaries. The route metric is named `route retention`; it is not labelled generator stability `s`. This increases T3 trace count by 2.5x and supersedes only the exploratory two-value T3 grid; all other registered gates remain unchanged.

The source is not declared complete merely because it compiles. Before accepting results, validate every gate, inspect all output schemas, verify the ten figure count, and update the report and manifest. Any timeout, provenance failure, guard failure, or invalid figure stops the campaign without retry.
