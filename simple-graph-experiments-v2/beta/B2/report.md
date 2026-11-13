# B2 axis-characterization report

**Date:** 2026-11-13  
**Status:** COMPLETE — generator-only characterization; no ns-3 protocol variants.

## Provenance

B2 used the A0-R2 patched YaDyGaGa tree pinned by B0:

- commit: `5a497f51815c85552fb0998b723460f16d0f50a0`
- tree: `32b243bc84b587f1782ead0d0ac56382a57425e5`
- timeline behavior: `patched`
- timeline seed: 42
- topology scope: geodesic, RGG, WS, ER, BA at N=42, realization r1
- frame-pool grid: `p_edge` = 0.3, 0.5, 0.7; trials = 3,000 and 10,000; pool seeds = 11, 29, 47

## Results

The run produced 1,710 characterization rows:

- path-life axis: 720 rows;
- stability axis: 180 rows;
- persistency axis: 810 rows;
- feasibility status: 1,710 feasible, 0 infeasible;
- errors: 0.

Life 1.0 was not generated. It remains the A4.5 static reference. No protocol simulation was run and no Beta protocol-variant budget was charged.

The persistency checks changed path-ID retention from approximately 0.0744 at persistency 0.1 to approximately 0.8884 at persistency 0.9 in the representative pool, consistently across the five N=42 families. Boolean timeline realization and frame-pool counts remain unchanged by persistency, as required by the patched implementation. Route-level shortest-path identity metrics are recorded in `results.csv`; these are generator/oracle observations, not AODV or OLSR results.

All rows and the provenance summary are in [results.csv](results.csv) and [summary.json](summary.json). The executable is [run_b2.py](run_b2.py).

## Gate interpretation

B2 confirms that the registered path-life, stability, and persistency controls can be characterized on the N=42 skeletons with the pinned patched build and the A2 frame-pool grid. Persistency is not inert at the path-ID level. This does not authorize B3 or any protocol sweep; those require a separate user decision after review.

The result is descriptive only. No ranking, ceiling, causal routing claim, or cross-family inference is made.
