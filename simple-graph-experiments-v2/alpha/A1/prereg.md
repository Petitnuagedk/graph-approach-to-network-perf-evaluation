# Alpha A1 preregistration — graph families and structural covariates

**Registered:** 2026-10-09, before generating any A1 graph. This follows the A0 disposition recorded in `alpha/gates.md`. No A2 generation, ns-3, protocol variants, or edits to existing generator files are authorized here. All code, outputs, and reports for this stage are confined to `simple-graph-experiments-v2/alpha/A1/`. All newly restated thresholds are **written after A0-R2 results**; the inherited A1 targets below are not changed.

## Stage scope and immutable boundary

Implement graph construction and measurement in a new, self-contained wrapper; read-only import of `icosahedral_geodesic.py` is allowed for the deterministic class-I geodesics. Do not import or modify `G2DG-SPC.py`, YaDyGaGa, or any Phase 0–7 output. There are no dynamic traces in A1. Protocol-variant spend is 0.

## Families, sizes, and counts

Build sizes `N=42, 92, 162` for every family, with actual N recorded:

1. **Geodesic:** class-I icosahedral subdivisions `nu=2,3,4`, generated as `(m,n)=(nu,0)`. One deterministic realization per size. Required vertices `10 nu^2+2`, edges `30 nu^2`, connected; degree exactly 5 on 12 vertices and exactly 6 on all remaining vertices.
2. **Random geometric:** three independent connected realizations per N, with points iid uniform on the unit square torus. Connect vertices when toroidal Euclidean distance is at most `r_N=sqrt(6/(pi*(N-1)))`, giving the stated mean-degree target about 6 without empirical tuning. Nodes are integer IDs `0..N-1`.
3. **Watts–Strogatz:** three independent connected realizations per N, `k=6`. Select a per-N rewiring probability from the fixed ascending grid `(0.01,0.05,0.10,0.20,0.30,0.50,0.80,1.00)`: for each grid value construct one connected calibration candidate at its preregistered calibration seed; choose the first candidate whose diameter differs from the deterministic geodesic diameter for that N. A disconnected calibration candidate is logged and skipped. Report the selected p, calibration seed, and diameter. If no grid candidate is connected and has a different diameter, stop and ask; do not extend the grid or tune further. The final three realizations use separate preregistered seeds and the selected p.
4. **Erdos–Renyi:** three independent connected realizations per N using `G(n,p)` with `p=6/(N-1)` (expected mean degree 6). Regenerate disconnected candidates; log each rejection and accepted attempt.
5. **Barabasi–Albert:** three realizations per N, `m=3` (expected mean degree approximately 6). If a candidate is disconnected, treat it under the common rejection budget below and log it.

Every random realization uses at most 1,000 candidate attempts (attempt indices 0–999); any disconnected candidate is rejected, including in families for which connectedness is expected. Candidate seed is `base_seed + attempt_index`; the accepted actual seed and rejected seed list are recorded. If any required realization cannot be made connected within 1,000 attempts, stop immediately and ask; do not report A1 as passed. Random families have exactly 3 accepted realizations per `(family,N)`, geodesic exactly 1, totaling 42 accepted graphs if complete. Rejected candidates are not accepted realizations.

## Seeds (fixed before generation)

For accepted random graph candidates, realization base seed is `1,000,000 + family_code*100,000 + N*10 + realization`, where realization is 1, 2, or 3 and family codes are `RGG=1`, `WS=2`, `ER=3`, `BA=4`. If rejection occurs, candidate seeds increment from this base. Thus, for example, RGG N=42 seeds start at 1,100,421–1,100,423; WS N=92 at 1,200,921–1,200,923; ER N=162 at 1,301,621–1,301,623; BA N=162 at 1,401,621–1,401,623. Geodesics are deterministic and use no random seed. WS calibration candidate seed for each N and grid index `j=1..8` is `2,000,000 + N*100 + j`; calibration attempts are single candidates per p, not accepted final realizations.

Within each random graph constructor use NetworkX's documented seeded generator. RGG point coordinates use Python `random.Random(seed)` in node order; toroidal distance is `sqrt(min(dx,1-dx)^2+min(dy,1-dy)^2)`. ER, WS, and BA use NetworkX 2.8.8 seeded constructors. Record Python/NetworkX/NumPy versions, exact commands, source hashes, p/r parameters, seeds, and every rejection.

## Pair rule and graph-level measurements

For each graph, designate one unordered probe pair by a deterministic structural rule fixed before generation: among every unordered node pair, maximize the exact number of equal-length shortest paths; break ties by greater shortest-path distance; break remaining ties lexicographically by the ordered pair of node labels. Compute shortest-path multiplicity by BFS distance-layer path counting (arbitrary-precision integer counts); do not enumerate/store every path. The selected pair is oriented lexicographically as S then R. Record the pair, hop distance, multiplicity, and the rule result. This rule deliberately seeks a pair for which path identity can matter without selecting after experimental outcomes.

For every accepted graph record N, edge count, mean degree, maximum degree, degree Gini (population definition `sum_i sum_j |d_i-d_j| / (2*N*sum_i d_i)`, or 0 if all degrees are 0), diameter, mean shortest-path length over unordered pairs, average clustering coefficient, connectedness, probe pair and exact equal-shortest-path multiplicity, plus the all-pairs hop-distance histogram with both pair counts and fractions. Include enough identity/seed fields to link each row to raw edge-list data.

## Matching and numerical gates

- Target mean degree for all families is 6. For each `(family,N)` report the mean across accepted realizations and per-realization range. Flag the family/size cell if `abs(family-cell mean degree - 6) > 1.0`; additionally list any individual realization exceeding that deviation. The >1.0 flag threshold is **written after A0-R2 results**, inherited here from the A1 specification, and is descriptive (do not tune or reject graphs because of it).
- For each N, produce a pairwise family mismatch table: absolute difference in family-cell mean degree and absolute difference in family-cell mean diameter for every unordered family pair; retain per-realization ranges in the underlying covariate table. No graph is selected or retuned based on the mismatch table.
- A1 passes only if all 42 required graphs were generated and connected; all three geodesics match the formula and exact degree-count requirement; the covariate, hop-distribution, mismatch, and flag tables are written; each selected WS calibration candidate differs from its same-N geodesic reference by at least one hop; and all rejection/calibration logs and hashes are present. Final WS realization diameters are reported as observed and are not rejected/tuned based on diameter. These conditions are descriptive and do not assert that random families are matched.
- Stop and ask if a geodesic verification fails, a required graph cannot be connected within the rejection budget, the WS p grid is exhausted without a diameter mismatch, or completing any gate would require changing an inherited frozen threshold. No threshold may be relaxed.

## Planned artifacts and execution

`run_a1_graphs.py` writes only within `alpha/A1/results/`: accepted graph edge lists, per-graph covariates, all-pairs hop histograms, family-size summary, pairwise mismatch, flags, and rejection/calibration logs. The report is `alpha/A1/report.md` and includes exact commands and SHA-256 for each generated table. The preregistration SHA-256 must be appended to `alpha/gates.md` before the first generator invocation; no A1 generation may precede that gate-log entry.
