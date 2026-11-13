# Alpha A1 — graph families and structural covariates

**Disposition:** completed on corrected, preregistered seed allocation. All 39 declared graph instances are connected; all class-I geodesic checks pass; WS calibration succeeded at every size; no mean-degree flag exceeded 1.0. This is static graph characterization only: **0 protocol variants, no ns-3, no existing-generator edits, no A2 execution.**

## Registration and corrections

- Original preregistration: [prereg.md](prereg.md), SHA-256 `a199ba5509ec8f00f503e3bb689a3845c48cb4edeb73e1dd20d1c1bdb67760a1`.
- Pre-final-generation correction: [preregistration addendum 1](prereg_amendment_1.md), SHA-256 `15df9008915e9d0c20725837366dedb727474347c82aacc6610c0aae6c45aea0`.
- The original preregistration had two clerical/method-record errors caught after its preliminary wrapper run: the declared design totals **39** graphs (3 geodesics + 4 random families × 3 sizes × 3 realizations), not 42; and `base_seed + attempt` could overlap adjacent realization seed ranges after rejections. Preliminary output was superseded. The amended disjoint blocks were registered before final regeneration; graph parameters, target distributions, selection rules, thresholds, and rejection budget were unchanged. The final accepted candidate seeds are all unique. The preliminary run's observations are not used in this report.
- One earlier wrapper invocation stopped with `ModuleNotFoundError` before constructing any graph; the import root was corrected before the preliminary construction run.

## Design and execution

Sizes are N=42, 92, 162. Families are deterministic class-I geodesic (nu=2,3,4; one each) and random geometric, Watts–Strogatz, Erdős–Rényi, and Barabási–Albert (three realizations per family and size). The corrected total is 39 accepted graphs. Random geometric graphs use a unit-square torus and radius `sqrt(6/(pi*(N-1)))`; WS uses k=6; ER uses `p=6/(N-1)`; BA uses m=3. Connectivity candidates were limited to 1,000 per required realization. The designated pair in each graph is selected by maximum number of equal-length shortest paths, then maximum hop distance, then lexicographically smallest ordered pair; the rule was fixed before generation.

Python 3.14.4, NetworkX 2.8.8, NumPy 1.26.4. Geodesic source was read-only [icosahedral_geodesic.py](../../../icosahedral_geodesic.py), SHA-256 `baa2dbfb551d971ab17437cd1e7c763cb66956bafb485a68b2ca59f9629d9524`. A1 wrapper SHA-256: `164e77766044511cef231c6dc199fe3e357d22b5b53309302181e5a7bc578f9d`.

Final generation command:

`PYTHONPYCACHEPREFIX=/tmp/alpha-a1-pycache /home/hledirach/Documents/J2/.venv/bin/python /home/hledirach/Documents/J2/simple-graph-experiments-v2/alpha/A1/run_a1_graphs.py`

Output: 39 accepted / expected, all 39 connected, no degree flags, WS selected p=0.01 at all three sizes. The measurement tables are linked below; each accepted per-graph edge-list has its own hash in [graph_manifest.json](results/graph_manifest.json).

## Geodesic verification

| nu | N | Expected / actual edges | Degree-5 vertices | Degree-6 vertices | Connected | Result |
|---:|---:|---:|---:|---:|---|---|
| 2 | 42 | 120 / 120 | 12 | 30 | Yes | Pass |
| 3 | 92 | 270 / 270 | 12 | 80 | Yes | Pass |
| 4 | 162 | 480 / 480 | 12 | 150 | Yes | Pass |

The exact check rows are in [geodesic_verification.csv](results/geodesic_verification.csv). No geodesic stop condition was triggered.

## Per-family covariate summary

Values aggregate the accepted realizations in that family/size cell. Mean edges, degree, Gini, diameter, mean shortest path, and clustering are realization means; max degree is the maximum observed among realizations; diameter range and probe-path multiplicity range show between-realization spread. All graphs are connected. Full-precision per-graph values, designated pairs, seeds, radii/probabilities, and acceptance attempts are in [graph_covariates.csv](results/graph_covariates.csv).

| Family | N | Mean edges | Mean degree | Max degree | Degree Gini | Diameter mean [min,max] | Mean shortest path | Clustering | Equal shortest S–R paths [min,max] |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Geodesic nu=2 | 42 | 120.00 | 5.714 | 6 | .0357 | 6.00 [6,6] | 2.916 | .4286 | 90 |
| Geodesic nu=3 | 92 | 270.00 | 5.870 | 6 | .0193 | 9.00 [9,9] | 4.282 | .4130 | 640 |
| Geodesic nu=4 | 162 | 480.00 | 5.926 | 6 | .0116 | 12.00 [12,12] | 5.665 | .4074 | 4,250 |
| RGG | 42 | 115.33 | 5.492 | 10 | .1717 | 7.67 [7,9] | 3.391 | .5918 | 32–105 |
| RGG | 92 | 269.33 | 5.855 | 13 | .1981 | 10.33 [9,11] | 4.625 | .5678 | 62–364 |
| RGG | 162 | 483.67 | 5.971 | 13 | .2011 | 14.67 [13,16] | 6.495 | .5705 | 443–1,512 |
| WS, k=6 | 42 | 126.00 | 6.000 | 7 | .0195 | 6.33 [6,7] | 3.336 | .5684 | 32–68 |
| WS, k=6 | 92 | 276.00 | 6.000 | 7 | .0080 | 15.00 [13,16] | 7.201 | .5870 | 272–675 |
| WS, k=6 | 162 | 486.00 | 7 | .0073 | 22.67 [17,27] | 9.268 | .5862 | 1,155–9,180 |
| ER | 42 | 115.00 | 5.476 | 11 | .2225 | 4.33 [4,5] | 2.325 | .1442 | 19–21 |
| ER | 92 | 259.67 | 5.645 | 15 | .2238 | 5.33 [5,6] | 2.775 | .0626 | 21–30 |
| ER | 162 | 489.33 | 6.041 | 15 | .2108 | 6.00 [6,6] | 3.036 | .0316 | 26–47 |
| BA, m=3 | 42 | 117.00 | 5.571 | 19 | .3133 | 4.00 [4,4] | 2.211 | .2439 | 17–28 |
| BA, m=3 | 92 | 267.00 | 5.804 | 40 | .3318 | 4.33 [4,5] | 2.554 | .1575 | 28–36 |
| BA, m=3 | 162 | 477.00 | 5.889 | 45 | .3517 | 5.00 [5,5] | 2.797 | .1069 | 43–53 |

At N=92, the probe pairs that would be used if a later, separately authorized A2 proceeds are: geodesic 0–31 (9 hops, 640 shortest paths); RGG realization 1, 14–47 (7, 105); WS realization 1, 49–85 (13, 675); ER realization 1, 5–82 (5, 25); BA realization 1, 5–72 (4, 28). These all have multiplicity greater than one. This pair rule was applied from graph structure, not observed dynamic outcomes.

All-pairs hop distributions are recorded as per-graph distance-bin counts and fractions in [hop_distance_distribution.csv](results/hop_distance_distribution.csv).

## Watts–Strogatz diameter calibration

| N | Geodesic diameter | Selected p | Calibration seed | Calibration diameter | Difference |
|---:|---:|---:|---:|---:|---:|
| 42 | 6 | .01 | 2,004,201 | 7 | +1 |
| 92 | 9 | .01 | 2,009,201 | 14 | +5 |
| 162 | 12 | .01 | 2,016,201 | 18 | +6 |

The fixed ascending p grid selected its first candidate at p=.01 for each N. The final independent WS realization diameters are reported without filtering: 6–7, 13–16, and 17–27 at N=42,92,162, respectively. Thus one final N=92 realization matches the geodesic diameter; the preregistered calibration candidate and chosen p meet the required difference, and the overlap among final realizations is explicitly retained rather than tuned away. See [ws_calibration.csv](results/ws_calibration.csv).

## Matching table: pairwise family mismatch

Each entry is `absolute mean-degree difference / absolute mean-diameter difference`, with family-cell means taken over accepted realizations. Values are rounded to three decimals; [family_pair_mismatch.csv](results/family_pair_mismatch.csv) has full precision.

| N | Family pair | Δ mean degree | Δ mean diameter |
|---:|---|---:|---:|
| 42 | Geodesic–RGG | .222 | 1.667 |
| 42 | Geodesic–WS | .286 | .333 |
| 42 | Geodesic–ER | .238 | 1.667 |
| 42 | Geodesic–BA | .143 | 2.000 |
| 42 | RGG–WS | .508 | 1.333 |
| 42 | RGG–ER | .016 | 3.333 |
| 42 | RGG–BA | .079 | 3.667 |
| 42 | WS–ER | .524 | 2.000 |
| 42 | WS–BA | .429 | 2.333 |
| 42 | ER–BA | .095 | .333 |
| 92 | Geodesic–RGG | .014 | 1.333 |
| 92 | Geodesic–WS | .130 | 6.000 |
| 92 | Geodesic–ER | .225 | 3.667 |
| 92 | Geodesic–BA | .065 | 4.667 |
| 92 | RGG–WS | .145 | 4.667 |
| 92 | RGG–ER | .210 | 5.000 |
| 92 | RGG–BA | .051 | 6.000 |
| 92 | WS–ER | .355 | 9.667 |
| 92 | WS–BA | .196 | 10.667 |
| 92 | ER–BA | .159 | 1.000 |
| 162 | Geodesic–RGG | .045 | 2.667 |
| 162 | Geodesic–WS | .074 | 10.667 |
| 162 | Geodesic–ER | .115 | 6.000 |
| 162 | Geodesic–BA | .037 | 7.000 |
| 162 | RGG–WS | .029 | 8.000 |
| 162 | RGG–ER | .070 | 8.667 |
| 162 | RGG–BA | .082 | 9.667 |
| 162 | WS–ER | .041 | 16.667 |
| 162 | WS–BA | .111 | 17.667 |
| 162 | ER–BA | .152 | 1.000 |

## Mean-degree flags, connectivity, and rejections

No family/size cell exceeded `abs(mean degree - 6) > 1.0`; no individual realization exceeded the same threshold. All 15 family-size flag rows are explicitly recorded in [mean_degree_flags.csv](results/mean_degree_flags.csv). All 39 accepted graphs passed connectedness. The 36 random graph realizations needed 47 candidate attempts: 11 disconnected RGG candidates were rejected (N=92: 5; N=162: 6); all candidates in WS, ER, and BA were connected on their first attempts. No realization approached the 1,000-attempt budget. Exact candidate seeds and statuses are in [generation_attempts.csv](results/generation_attempts.csv); there were no ER rejections in the final amended-seed run.

The A1 gate is met under the registered arithmetic correction: all requested family/size/realization cells were produced (39 total); geodesic counts/degrees pass; covariate, pairwise mismatch, hop-distribution, flag, and calibration/rejection records exist; each WS calibration candidate differs from its geodesic diameter; all graphs are connected. The preregistration count correction is documented, not hidden.

## Artifacts and hashes

Each table hash below is SHA-256 of the final corrected-seed artifact. The edge-list manifest includes the SHA-256 of each individual graph edge-list.

| Artifact | SHA-256 |
|---|---|
| [geodesic_verification.csv](results/geodesic_verification.csv) | `e802bf8c50be6d32e6a68e89df9c0b110e5a06732c44f846034f56435dff1232` |
| [graph_covariates.csv](results/graph_covariates.csv) | `51895a726c14bbb013b2996b7aa14b37a1a8103ee052f70ab1564c4ac3de8759` |
| [hop_distance_distribution.csv](results/hop_distance_distribution.csv) | `bb4ecfa7170447653b14ea55069b9e7c6c47c2ed8c6eda014211381943007404` |
| [family_size_summary.csv](results/family_size_summary.csv) | `4c239c55359675c376639fb6d8c59a962787374d5e4b4326452c2541b1891926` |
| [family_pair_mismatch.csv](results/family_pair_mismatch.csv) | `c8a69408b45abe72cb0cfd3de303d2cad16bde3f68ea91ab6185d3958f7f2023` |
| [mean_degree_flags.csv](results/mean_degree_flags.csv) | `e77aaca45d4344c5329d3b344e30859f0e3e1b16f7c5a36deeb36e14b5298eb3` |
| [ws_calibration.csv](results/ws_calibration.csv) | `bab7314ad4a861952836e4549de2f49b9302e73a79b604c88c7630554f6a4765` |
| [generation_attempts.csv](results/generation_attempts.csv) | `f8df5445827dbcf4cf9cec71cf197ddac370d43332b0c4c29e7ad77b2b143834` |
| [graph_edges.csv](results/graph_edges.csv) | `810d487bfc77253dec1da14fd02f737b676cf1e88c483af109f09367e78ff172` |
| [graph_manifest.json](results/graph_manifest.json) | `b1b02780436404591f6b218b1eb465da7a7ef661bc9ee86df54cb8c9fe4649d7` |

## Decisions requested

1. Approve or amend the proposed A2 diversity criterion in the not-yet-executed [A2 preregistration](../A2/prereg.md): normalized mean D >= .30; at least five unique timelines; fraction of selected-seed pairs with D < .10 below 5%; and maximum duplicate group <=10% of the 200-candidate pool.
2. Confirm or amend the structural probe-pair rule (maximum equal-length shortest paths, then maximum hop distance, then lexicographic pair).
3. Confirm stability=.9 for A2. This is the proposed single fixed value because it makes both N=92 life=.5 and life=.9 exact timeline quotas feasible under the A0-R2 rule; the .9-life/.8-stability cell is infeasible in A0-R2. A2 remains preregistration-only and blocked from execution.
4. Confirm the corrected transition-count statement in [A2 preregistration](../A2/prereg.md): uptime and requested up-run count are fixed by construction, but total transitions can vary with the down-run category and boundary arrangement. The requested claim that both uptime and total transition count are fixed is not supported by the patched source.
