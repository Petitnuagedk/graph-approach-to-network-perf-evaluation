# Tango campaign preregistration

Registered 2026-10-21 before any Tango generation. This preregistration is frozen after the environment guard failed; no generator or analysis operation was launched. Scope is generator-only under `simple-graph-experiments-v2/tango/`; no existing generator, library, A1, A2, or A0R2 file is edited. No file under `alpha/A4*` was touched. No ns-3, graph-run, or protocol variant is authorized; variants spent = 0.

## Source and provenance
- Required isolated sampler: `alpha/A2f/A2f-2/source`, Git HEAD `2317b4f36eec77270a2b4f334ddd37ae4ee20b8d`, Git tree `89b344777d3581b74a2ab78724cf12819891df2e`; `yadygaga/__init__.py` SHA-256 `8484ab55108d8943ed984a7e258e317243c4f0530a0df627cb6b2150c1a569e6`; `yadygaga/timelineBlockGenerator.py` SHA-256 `5c0771a14a5b42810deb9d904f2eedbde5dcd92c08c600fa831623956854df0e6`. Its `SPCTimelineBlockGenerator` exposes `behavior='uk'`, `up_count=U`, and `up_runs=K`, with `mode='blocks'`.
- A1 manifest: `alpha/A1/results/graph_manifest.json`; graph edges: `alpha/A1/results/graph_edges.csv`; A1 pair rule: `alpha/A1/run_a1_graphs.py`, structurally max equal-length shortest-path count, then max hop distance, then lexicographically smallest ordered pair.
- A1 edge-list hashes must be verified before use; no graph was used because the guard stopped the campaign.
- New graph seed block, to be registered before a future generation restart: `TANGO-GRAPH-20261021`, reserved numeric range `30000000..30999999`, disjoint from A1 seeds and explicitly listed A1 calibration/candidate seeds. No seed was consumed.

## Fixed design and gates
T1: F=120; q=0.1..0.9; U=round(Fq); D=F-U; K=1..min(U,D+1); 200 exact-uniform schedules per cell, seeds 42..241; record uptime, K, transitions, up/down runs, outage, first outage, lag-1 autocorrelation. Use closed-form support M(U,K), brute-force check for F=8. T1-G1 mean up-run error <=1e-9; T1-G2 closed form equals brute force; T1-G3 all feasible cells complete within 60 s child-operation timeout; T1-G4 transitions in [2K-2,2K], otherwise provenance failure and stop.

T2: N={42,92,162}; geodesic one plus 30 accepted realizations for each random family RGG/WS/ER/BA (3 A1 + 27 new); A1 family parameters unchanged; connectivity rejection budget 1000 candidates/realization, all rejections logged. Record A1 covariates plus betweenness max and assortativity. T2-G1 connectedness and geodesic degree counts (12 degree-5, remainder degree-6); T2-G2 all random cells 30/30 accepted within budget; T2-G3 flag cell mean-degree deviation >1.

T3: all T2 graphs; lives .3,.5,.7; F=120; K=ceil(Kmax/2), Kmax=min(U,D+1), p_edge=.5, pathPersistency=.25,.75, 3000 pool trials, 120 frames, trace seeds 42..44 with offsets +10000 and +20000. Pilot one N=162 trace, then project and stop/ask if projection >12 h. Record exact pools, route groups, route retention, route-ID retention, hop statistics, uptime error, fallbacks, shortcuts. T3-G1 all operations, zero empty pools and shortcuts; T3-G2 uptime error <=.05.

T4: ER and geodesic, N={42,92,162}, p_edge={.3,.5,.7}, ER n=5 and geodesic n=1, 3000 candidate frames/pool, 3 pool seeds; record up/down fractions and supply ratios for life .5/.9. T4-G1 all operations complete; descriptive if not.

Analysis: sample SD ddof=1; graph realization is replication unit; bootstrap 10,000 realization resamples, seed 20261021, within family/N stratum; no frames/seeds as replicates. Spearman correlations stratified by family/N, life fixed; geodesic excluded (marker only); pooled fixed-N coefficients shown beside stratified, never pool N. Entangled: |rho|>=.7 and CI excludes .5. Decoupled: |rho|<.3 and CI upper <.5. C-G1 CI half-width <=.25 or label underpowered; C-G2 every coefficient labelled entangled/decoupled/inconclusive.

Figures are exactly P01..P10, each PNG at 200 dpi and PDF plus same-stem plotted CSV under `figures/data/`, Matplotlib only, colorblind-safe family encoding. Per-operation wall timeout is 60 s in a child process; timeout/error is a recorded failure and is never retried, clamped, or omitted. At most two workers, each launched with `nice -n 19`; before every batch require MemAvailable >=8 GiB and swap ==0. Timing is recorded only in CSV as `contended`, never claimed in prose.

Stop conditions: missing/non-`uk` sampler, A1 hash mismatch, memory/swap guard violation, pilot projection >12 h, T1-G4 failure, empty pool, shortcut frame, or any gate failure invalidating a figure. Historical artifacts remain immutable; any future correction is an amendment.
