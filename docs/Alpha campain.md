# Phase Alpha: YADYGAGA capability study and static calibration on large graphs (no dynamics campaign)

## Research question for the whole Alpha-Delta series
How do topology and link dynamics impact routing-algorithm (RA) performance and network behavior?
Alpha does not answer it. Alpha establishes (i) what the YADYGAGA generator can do at scale, (ii) which family/size/protocol combinations are measurable at all, and (iii) the load and warm-up values that later phases will use.

## Dependencies and stop conditions
- Read phase7/phase7_report.md. If gate 7B (no-interpolate channel verification) did not pass, STOP and report. Use the 7B channel settings (no interpolation, the justified down-loss value) in every Alpha run.
- Read phase7 7D (generator diagnosis and proposal) and phase7 7C outcomes. Alpha uses NO static-route reference variant unless 7C passed its gate. The oracle is trace-derived time-respecting reachability.

## Hard rules
- Do not modify or delete anything in simple-graph-experiments/ or simple-graph-experiments-v2/phase1..phase7. Outputs go to simple-graph-experiments-v2/alpha/.
- Do not modify existing generator files (YADYGAGA library, G2DG-SPC.py, graph/DG scripts). All adaptation lives in new wrapper modules under alpha/. Any change to an existing generator file requires my approval; propose it in the report instead.
- Gated order: A0, A1, A2, A3, A4. Do not start a stage before the previous gate is recorded in alpha/gates.md.
- Before running anything in a stage, write alpha/<stage>/prereg.md with numeric thresholds for every gate in that stage. No gate may end "undecided" for a missing threshold.
- Budget counts PROTOCOL VARIANTS (graph-run invocations x routing variants). Cap for Alpha: 300. Log the running total in alpha/budget.md after every batch. Also state per-run wall time per (family, N, protocol) as measured, and a projected total wall time before each batch above 50 variants. If the projection exceeds 24 h, stop and ask.
- Beta cap-counting unit is **protocol variants** (graph-run invocations × routing variants), not bare invocations, packets, frames, or elapsed time. This defines only the unit; Beta's numeric cap remains unset until it is stated in an approved Beta preregistration. This accounting-unit decision does not authorize Beta work.
- No protocol ranking, no ceiling language, no PDR normalization to a static reference. Report sample SD (ddof=1) and per-realization values. Replay epochs are never independent realizations.
- New ns-3 flags are opt-in; a legacy regression case must stay byte-identical (timing columns excluded).
- Record config.json (args, seeds, source hashes, ns-3 version) for every run. The repo is dirty and ns-3 is not a git repo, so hashes are the identifier.

## A0. YADYGAGA capability study (read-only, no simulation)
Locate the YADYGAGA library (report path, version or hash). Read the code and its documentation. Do not assume any behavior; cite file and line for every statement. Answer in alpha/A0/yadygaga_capabilities.md:
1. Path constraints: can it constrain several S-R paths simultaneously? Disjoint pairs only, or shared nodes? Maximum number of constrained paths? Parameters per path (path life, stability, persistency)? How are constraints specified (API and file formats)?
2. Persistency: exact semantics of the persistency parameter. What is persisted (path identity, edge set, node set), over which time scale, and what happens at 0 and 1? How does it interact with stability and path life? Give a worked example on a small graph.
3. Unconstrained links: how are they toggled? i.i.d. per frame or persistent? Which parameters control fraction up and link lifetime, and are they independent of each other? Are the random toggles applied to skeleton edges only, or can edges outside the skeleton appear? Does the stability parameter affect them?
4. Randomness: which RNG draws the S-R timeline, which draws the random links, and where the seed enters (this links to 7D). Does a different seed give a different S-R timeline at N=40, 90, 160?
5. Outputs and scale: what measured properties does it return? Wall time and memory at N=42, 92, 162 for 60 and 120 frames (run it, three repetitions, record timings).
6. Limits and failure modes: what does it do when the constraint is infeasible (path life too high for the skeleton, path too long)? Does it silently relax?
Decision rule written in prereg before the study. YADYGAGA is "usable" for Beta if ALL hold: (a) it can constrain at least one probe path and ideally several; (b) its random-link process has at least two controls separable into fraction-up and lifetime, or its documented behavior can be characterized by measuring both; (c) different seeds give at least 5 distinct S-R timelines with mean pairwise Hamming distance above 0.1 at N=92 for path life 0.5; (d) generation of one trace at N=162 takes under 10 minutes; (e) measured S-R uptime is within 0.05 of requested path life at N=92 for path life 0.3, 0.5, 0.7.
If YADYGAGA is NOT usable, or only partly usable, write a design note for the Edge-Markovian fallback instead of silently switching. Fallback spec: each skeleton edge follows an independent two-state chain with stationary up fraction pi and mean up duration L frames (p10 = 1/L, p01 = pi*p10/(1-pi)); the realized S-R usable uptime, up-run list, hop count and transition count are logged for every trace. State what the fallback loses: no controlled path life, S-R uptime becomes an output.
If it is partly usable (for example single constrained path only, or persistent but not tunable random links), say exactly which Beta axes it supports and which require the fallback.
Gate A0: the written capability report plus a "usable / partly usable / not usable" verdict per Beta axis (path life, stability, persistency, random-link fraction, random-link lifetime, number of constrained paths), each with the evidence line. Stop for my review if the verdict is "not usable" for path life or seed diversity.

## A1. Graph families and structural covariates (no ns-3)
Families and sizes (N approximate, document actual values):
- geodesic polyhedron, icosahedral class I, frequency nu = 2, 3, 4 (N = 10 nu^2 + 2 = 42, 92, 162); verify degree 5 on exactly 12 vertices and 6 elsewhere; 1 realization (deterministic)
- random geometric graph tuned to mean degree about 6
- Watts-Strogatz, degree 6, rewiring probability chosen so that diameter differs from the geodesic one (report it)
- Erdos-Renyi tuned to mean degree about 6 (connected giant component required; regenerate until connected, log rejections)
- Barabasi-Albert with m = 3 (mean degree about 6)
Sizes N = 42, 92, 162 for all families (random families use the nearest feasible N). Random families: 3 realizations per (family, N); geodesic: 1.
Log for every graph: N, edges, mean/max degree, degree Gini, diameter, mean shortest-path length, clustering coefficient, connectivity, and (for sampling) the hop-distance distribution over all pairs.
Matching report: for each size, a table showing how far each family is from the others in mean degree and diameter. Do not tune anything beyond the stated targets; just report the mismatch (Gamma will decide matching).
Gate A1: all graphs connected, geodesic counts verified, covariate table written, and the family/size cells with a mean-degree deviation above 1.0 from the target flagged.

## A2. Generator feasibility at scale (trace generation only, no ns-3)
Using the A0 verdict (YADYGAGA where usable, otherwise the Edge-Markovian fallback), generate for one size per family (N about 92), 5 seeds, path life 0.5 and 0.9 (or the closest the generator allows), 120 frames:
1. Timeline diversity audit: number of distinct serialized S-R timelines per cell and mean pairwise Hamming distance.
2. Measured features per trace: S-R usable uptime, up-run list, mean up-run, transitions, S-R hop count over time, fraction of frames with a shorter-than-constrained path (shortcuts).
3. Report how much random links dilute the constraint: the difference between requested path life and the measured time-respecting S-R reachability.
Gate A2: at least 5 distinct timelines per cell with mean pairwise Hamming distance above 0.1, measured uptime within 0.05 of requested. If a family fails, say whether the fallback would pass, and stop for my review. Do not launch ns-3 runs on traces that fail the diversity audit.

## A3. Instrumentation (code changes, opt-in, with tests)
Extend graph-run.cc, opt-in flags only. Cite the ns-3 3.46.1 trace sources used.
1. Many-flow support: `--flowFraction=<phi>` selecting phi x (N(N-1)/2) unordered pairs uniformly at random (direction random, seeded, pair list written to flows.csv with hop distance in the static skeleton), plus one designated probe flow that is always included and excluded from the background count. Start times staggered over the first second to avoid synchronized starts.
2. Per-flow outputs: offered, delivered, delay quantiles (median, p95), hop distance.
3. Per-node outputs: control packets and bytes Tx by message type, forwarded data packets, MAC Tx retries and drops, PHY Rx drops by reason (collision or interference versus below sensitivity), queue drops, route table size at 1 Hz (optional).
4. Convergence detector: time of first delivered probe packet and time after which probe PDR in a sliding 10 s window stays at or above 0.99.
Tests: a small hand-checkable graph (path of 4 nodes, one flow) where per-node counts are known. Regression: the legacy case byte-identical.
Gate A3: unit tests pass; per-node forwarded packets summed over nodes equals total data packet hops from delivered paths on the test graph.

## A4. Static calibration
Settings: all links up for the whole run; use the 7B channel; 802.11g, 20 dBm, 50 kbps, 1024 B per flow.
Step 4.0, runtime pilot (6 variants): N=162 geodesic, 3 protocols, phi=1% and 10%, 120 frames. Report wall time and memory. If the projected wall time for 4.2 exceeds 24 h, stop.
Step 4.1, convergence (probe flow only, no background, no warm-up, 240 frames): one graph per (family, N) class, 3 protocols = 45 variants. Report convergence time against N and diameter (separately), per protocol. Define the warm-up for later phases as 1.5 x the maximum convergence time observed per protocol and size, rounded up to whole frames; state it per protocol and size. Do not reuse the 45 s of earlier phases. Note that Phase 6D found a 15 s DSDV outage at 60 s warm-up on an all-up replay; check whether any DSDV run shows a comparable gap.
Step 4.2, load sweep: one graph per class (15), phi in {1%, 5%, 10%}, 3 protocols = 135 variants. Warm-up from 4.1. Report per run: probe PDR, median and p10 of background per-flow PDR, delay median/p95, control packets and bytes per node (mean, max, Gini), forwarded-load Gini, MAC retries per node (max), PHY collision drops per node (max). Place the MAC and collision numbers next to every PDR in the tables.
Step 4.3, replication at the chosen operating load (see gate) for the extra random-family realizations: 4 random families x 3 sizes x 2 extra realizations x 3 protocols = 72 variants.
Operating load: the highest phi in {1%, 5%, 10%} for which, for a given size, the pass criterion below holds for every protocol that is retained at that size. If 5% fails but 1% passes at some size, add phi = 2% for that size only, and log the extra variants in the budget.
Pass criterion for a (family, N, protocol) cell at a load: probe PDR >= 0.99 and background median per-flow PDR >= 0.95 after convergence. A cell that fails at the lowest load is dropped from later phases, documented with its measured cause (no route, MAC saturation, queue drops). A protocol that fails on every large-N cell is formally dropped (this includes DSDV if so).
Collision attribution rule: if a protocol's PDR drop at higher phi coincides with PHY collision drops or MAC retries at the max-degree node above a threshold preregistered before the run, report the failure as MAC contention, not a routing effect.
Gate A4: every (family, N, protocol) cell has an explicit status (pass at phi / dropped, with cause), warm-up values per protocol and size are fixed, runtime per run is recorded, and total variants <= 300.

## Deliverables
 alpha_report.md with: A0 capability report summary and the verdict table; A1 covariate and mismatch tables; A2 audit results; A3 test results; A4 tables (convergence, load sweep, status matrix); budget used; exact commands; SHA-256 of generated tables; list of Alpha claims that are limited by single graph realizations; and a short list of decisions needed from me: YADYGAGA versus Edge-Markovian per Beta axis, operating load per size, whether to define load as a fraction of nodes instead of pairs if 10% saturates, the retained families/protocols, and Beta's numeric cap (its counting unit is already fixed as protocol variants). No Beta work, no dynamic campaign, no ranking.