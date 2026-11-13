# Alpha A0-R2 — sampler diagnosis, diversity scaling, and provenance

**Status:** offline A0-R2 measurements complete; frozen A0 gates pass on the isolated rebased patched mode. Historical A0 failure and A0-R results remain unchanged. No ns-3, protocol variants, or A2 work. `alpha/gates.md` now records the user's authorized A0 disposition for A1 graph-family work only.

## Registration and boundaries

A0-R2 preregistration was written and hash-logged before any generator measurement: [preregistration](prereg.md), SHA-256 `e9cc6b10a7badb41a82bf06b1dbc7a2096901943b3dbcb7ca4e2812880c761d3`. One clarification before execution distinguished infeasible $M=0$ cells from a narrow but nonempty support. Every new threshold is marked in the preregistration as “written after A0-R results”: run-count-marginal uniformity diagnostic rejection level .01; 1st-percentile distinct-count shortfall; proposed mean normalized diversity $D\ge .30$. The latter is a post hoc A2 design proposal, **not an approved replacement** for the frozen A0 rule.

All code/data are confined to `alpha/A0R2/`. A0/A0-R source trees and external YaDyGaGa working files were not edited. The external `timelineBlockGenerator.py` and `toolbox.py` working diffs were empty when audited; the earlier A0 “dirty” designation was accurate at its audit time but is no longer current.

## 1. Support size, concentration, and exact-uniform sampler

For $F=120$, $U=\operatorname{round}(Fq)$, $D=F-U$, and stability run target $K=\operatorname{round}(1+(1-s)(U-1))$ clamped to $1..U$, an exact schedule requires $K\le D+1$. For nontrivial $0<U<F$, exact support is

$$M=\binom{U-1}{K-1}\sum_{J=\max(1,K-1)}^{\min(D,K+1)} b(K,J)\binom{D-1}{J-1},$$

where $b=2$ when $J=K$ (either boundary state) and $b=1$ when $J=K\pm1$. This counts output S–R **Boolean bit timelines**, not candidate graphs or assembled graph traces. For all-up/all-down edge cases, $M=1$. Infeasible exact quotas have $M=0$.

The closed form was exhaustively checked against all $2^8$ strings for every life/stability cell at $F=8`; all 15 counts matched. See [small-frame brute force checks](results/small_frames_bruteforce_uniform.csv).

First, the original A0-R seeded-composition sampler was measured over seeds 42–241. In every feasible cell it drew each of the three possible down-run categories almost exactly equally, even though their output-string counts are very unequal; the registered Pearson Monte Carlo diagnostic rejected that run-count marginal in all feasible cells ($p=10^{-5}$). The most consequential constrained cell, life=.5/stability=0, produced 52 unique schedules out of 200 from $M=61$, versus 58.76 expected under uniform draws, still within the uniform 1st-percentile bound 55. This is support-level concentration, not “narrow by construction.”

Per the preregistered remediation rule, the A0R2 patched mode now selects the down-run category by exact integer weight $b(K,J)\binom{U-1}{K-1}\binom{D-1}{J-1}$, draws positive up/down compositions uniformly, and selects a legal boundary arrangement uniformly. Every supported output string has equal probability by this one-to-one category/composition/boundary representation. The original later-upstream behavior remains selectable as `behavior="legacy"`; exact seeded mode is the default `behavior="patched"`. Exhaustive $F=8$ support-count checks pass. Under 200 seed draws from the corrected sampler, no run-count marginal test rejected at the preregistered .01 level. This is evidence on the tested marginal plus a construction proof, not a claim that finite samples can certify arbitrary high-dimensional PRNG properties.

| Life | Stability | $U/K$ | Exact $M$ | Unique / 200 | Raw Hamming mean [min,max] | Mean normalized $D$ | Largest duplicate group | Uniform expected unique | Run-count $p$ | Frozen A0 descriptive rule | Post hoc $D\ge.30$ rule |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| .1 | 0.0 | 12/12 | 3,133,614,810,784,185 | 200 | .1800 [.1000,.2000] | .9000 | 1 | 200.00 | .8631 | Pass | Pass |
| .1 | .4 | 12/8 | 125,369,919,687,870 | 200 | .1802 [.1000,.2000] | .9008 | 1 | 200.00 | .6811 | Pass | Pass |
| .1 | .8 | 12/3 | 11,546,370 | 200 | .1797 [.0333,.2000] | .8984 | 1 | 200.00 | .6784 | Pass | Pass |
| .3 | 0.0 | 36/36 | 1,244,981,450,259,157,662,259,650 | 200 | .4192 [.2333,.5667] | .6986 | 1 | 200.00 | .6665 | Pass | Pass |
| .3 | .4 | 36/22 | 293,278,189,642,330,420,512,372,960,000 | 200 | .4200 [.2667,.5667] | .6999 | 1 | 200.00 | .6191 | Pass | Pass |
| .3 | .8 | 36/8 | 323,614,239,197,792,400 | 200 | .4168 [.1833,.6000] | .6946 | 1 | 200.00 | .4261 | Pass | Pass |
| .5 | 0.0 | 60/60 | 61 | 59 | .3591 [.0000,1.0000] | .3591 | 8 | 58.76 | .5675 | Pass | Pass |
| .5 | .4 | 60/36 | 1,902,870,077,593,125,142,439,497,038,077,235 | 200 | .5001 [.3167,.6833] | .5001 | 1 | 200.00 | .9720 | Pass | Pass |
| .5 | .8 | 60/13 | 7,350,800,972,159,737,295,248,500 | 200 | .4960 [.2333,.7167] | .4960 | 1 | 200.00 | .6505 | Pass | Pass |
| .7 | 0.0 | 84/84 | 0 | — | — | — | — | — | — | Infeasible | Infeasible |
| .7 | .4 | 84/51 | 0 | — | — | — | — | — | — | Infeasible | Infeasible |
| .7 | .8 | 84/18 | 3,601,332,440,851,846,551,457,414,500 | 200 | .4178 [.2667,.5667] | .6963 | 1 | 200.00 | .3152 | Pass | Pass |
| .9 | 0.0 | 108/108 | 0 | — | — | — | — | — | — | Infeasible | Infeasible |
| .9 | .4 | 108/65 | 0 | — | — | — | — | — | — | Infeasible | Infeasible |
| .9 | .8 | 108/22 | 0 | — | — | — | — | — | — | Infeasible | Infeasible |

“Frozen A0 descriptive rule” applies the historical requirement (≥5 unique and raw mean Hamming >.10) to these 200-seed cells for comparison; the historical gate itself remains the original life=.5/five-seed test and has not changed. The new normalized rule also passes every feasible cell; normalized diversity is not applicable to infeasible cells. For large $M$, the birthday expected unique count is effectively 200 and collisions are too rare for 200 draws to estimate the enormous support; expected colliding-pair values and run-count null probabilities are in the CSV. For $M=61$, expected colliding pairs are 326.23 and observed unique count 59 is compatible with uniform sampling.

Complete data: [post-fix cell summary](results/sampler_uniform_cells.csv), [per-seed Boolean strings](results/sampler_uniform_draws.csv), [original sampler diagnosis](results/sampler_cells.csv), [small-frame enumeration](results/small_frames_bruteforce_uniform.csv). The exact-uniform algorithm change affects only the A0R2 isolated copy.

The smallest feasible support in the registered grid is $M=61$ at life=.5/stability=0. Thus no feasible grid cell is “narrow by construction” under the preregistered $0<M<5$ rule; $M=0$ cells are separately labeled infeasible.

## 2. Diversity criterion comparison

Normalized $D=H/[2\min(q,1-q)]$ is reported in the table above. The old raw cutoff is passed in each feasible supplementary 200-seed cell. The proposed post hoc $D\ge.30$ rule also passes each feasible cell, including the relatively narrow but nonempty life=.5/stability=0 cell ($M=61$, 59 unique, mean $D=.3591$). This does not alter Alpha's frozen gate and does not authorize A2. Approval of this A2 criterion remains a decision for the user.

## 3. Infeasibility and safe region

Exact-mode infeasibility is exactly $K>D+1$. Both tested frame horizons have the same pattern across the grid:

| Life | Stability values feasible at F=60 and F=120 | Infeasible stability values at both frames |
|---:|---|---|
| .1 | 0,.4,.8 | none |
| .3 | 0,.4,.8 | none |
| .5 | 0,.4,.8 | none |
| .7 | .8 | 0,.4 |
| .9 | none | 0,.4,.8 |

For all ten infeasible cells, later upstream silently changes requested $K$ to $D+1$ and the tested legacy selector actually realizes that capped number of up-runs while keeping the rounded up quota. (F=60: .7/s0 42→19, .7/s.4 26→19; .9/s0 54→7, .9/s.4 33→7, .9/s.8 12→7. F=120: .7/s0 84→37, .7/s.4 51→37; .9/s0 108→13, .9/s.4 65→13, .9/s.8 22→13.) In exact patched mode these cells raise `ValueError`, rather than silently changing the run target. Per-cell rows: [infeasibility map](results/infeasibility_map.csv).

**Pinned A0 provenance correction:** this cap is present in the later upstream HEAD, not in the pinned clean A0 baseline. Inspection of pinned commit `51b01ac...` confirms its original selector did not clamp `up_blocks` to `down_count+1`; therefore the ten-cell capped-behavior statement above applies only to the archived later-HEAD legacy branch. The pinned A0 code instead attempts the requested composition. For a representative infeasible cell (F=120, life=.7, stability=.4; requested K=51 with D+1=37), an isolated execution with a two-second safety timeout did not return a completed timeline. This is recorded as a timeout, not as proof of a crash, a particular exception, or a cap. No pinned-A0 output is claimed for the full grid. The exact behavior comparison is therefore: later HEAD silently caps and completes the ten tested cells; pinned clean has no such cap and the representative isolated execution timed out; A0R2 patched mode rejects infeasible exact requests explicitly.

**Safe region for Beta:** at the requested horizon, stay within $K\le D+1$ (and life/stability in [0,1]); on this tested grid that means all stability values for life≤.5, stability=.8 for life=.7, and no .9-life cells. The exact inequality, not interpolation, governs untested values. Infeasible parameter requests cannot claim both the requested exact uptime and requested stability-derived run count.

## 4. Rebase, selectable behavior, and provenance

- Pinned A0 baseline commit/tree: `51b01ac7faa78a494c3baedc560d658f384afe09` / `5040cf6785fbb3a49cb48a7eb79eb7e4a19cbf9f`.
- Later upstream HEAD/date/tree: `fb053994e4cc5b590e49afb816b5d5e1be655217`, `2026-10-09T10:24:00+02:00` / `a065e1fe5ff1ce80ca57ef11edf548bcf482ea87`.
- A0R2 isolated patched-copy tree: `32b243bc84b587f1782ead0d0ac56382a57425e5` (local commit `5a497f51815c85552fb0998b723460f16d0f50a0`), composed from the later archive plus A0-R frame/assembly changes and the A0R2 selectable timeline implementation.
- Source SHA-256: A0R2 `timelineBlockGenerator.py` `c10fa53afaf4ce323835ed0ffd87de0322b6df7ccc63918c22736b409c13a8a4`; `frameGenerator.py` `e84971f89cb966a574bf447ce8135c0c241b407be14e5066db2f82f3c2ec6b4b`; `dynaGraph.py` `8e75cb59139516bfcc6ccfe672281575c4e8490fdf03d5d5bbcbef8a8b203c42`.
- The original A0-R patch does **not** apply cleanly to the later HEAD as a textual patch: `git apply --check .../A0R/yadygaga_a0r.patch` fails at `yadygaga/timelineBlockGenerator.py:55`. Expected overlapping changes include the later-upstream `up_blocks=min(up_blocks,down_count+1)` cap and `_split_counts` clamp, retained in the [legacy implementation](YaDyGaGa/yadygaga/timelineBlockGenerator.py#L221-L225). The resolution is isolated and explicit: the later-HEAD `generate_blocks()` implementation remains selectable as `behavior="legacy"`; `behavior="patched"` enters A0R2's exact seeded sampler at [the behavior selector](YaDyGaGa/yadygaga/timelineBlockGenerator.py#L127-L128). This intentionally preserves both semantic choices; it is not a claim that the upstream changes are behaviorally identical to A0-R. The patched mode does not cap exact requests. The isolated source commit and tree hash above, together with the source hashes below, define the A0R2 resolution.
- The selectable `behavior="legacy"` branch matched the archived later-HEAD implementation exactly in timeline and path-ID output for all ten infeasible life/stability/frame cells; capped realized up-run counts are listed above.
- The later upstream `toolbox.py`, including its tolerance for nonnumeric node labels, is retained in the [rebased copy](YaDyGaGa/yadygaga/toolbox.py); source-level changes are confined to the A0R2 copy.
- The seed-dependent patched path intentionally changes Boolean schedules. **Phases 1–7 traces generated through legacy behavior cannot be regenerated from the patched seed path and are not asserted equivalent.** Select `behavior="legacy"` to reproduce the later upstream timeline algorithm; it still does not establish identical provenance for all historical wrappers or environments.

The complete A0-R baseline patch remains available at [yadygaga_a0r.patch](../A0R/yadygaga_a0r.patch). The A0R2 resolution is represented by the modified isolated source and tree/hash above; no external checkout change was made.

### Frozen A0 criteria, rerun on rebased patched mode

| Frozen criterion | Result | Verdict |
|---|---|---|
| N=92, 120 frames, life=.5, seeds 42–46; ≥5 unique S–R timelines and raw mean Hamming >.10 | 5 unique; mean .5066667 | Pass |
| N=92 fidelity at life .3/.5/.7, five seeds each; each uptime error ≤.05 | 15/15 exact schedule quota; max assembled S–R uptime error 0 | Pass |
| N=162, 120 frames, seeds 42–44; each <600 s and pools nonempty | max .19773 s; up pools 460/456 groups, 466/464, 465/461; down pools 40,34,35 | Pass |

This rerun uses the corrected exactly uniform patched-mode sampler. A final verification rerun used a fresh `PYTHONPYCACHEPREFIX` to ensure archived bytecode could not shadow source; sampler summaries and all gate verdicts were unchanged. The refreshed maximum timing was 0.19773 s. Raw rows and timing are in [frozen_a0_rebased.csv](results/frozen_a0_rebased.csv), summary in [rebased_axis_summary.json](results/rebased_axis_summary.json). No A0 thresholds were changed.

## 5. Axis characterization on patched traces

### Stability vs. life and persistency

At life=.5, persistency=.75, seeds 42–51, fixed 120 frames:

| Stability | Mean transitions (min–max) | Mean up-run frames |
|---:|---:|---:|
| 0.0 | 118.0 (118–118) | 1.000 |
| .2 | 94.4 (94–95) | 1.250 |
| .4 | 70.9 (70–72) | 1.667 |
| .6 | 49.4 (48–50) | 2.400 |
| .8 | 25.6 (24–26) | 4.615 |

At fixed life, stability has a distinct effect on transition/run structure. At fixed stability, path-life changes the exact up quota; it also enters the stability-to-run formula through $U$, so the two axes are coupled in run count and must be reported as a controlled grid, not treated as globally orthogonal. Persistency did not alter Boolean schedules in 250 registered combinations (five stability values × ten seeds × five persistencies); it controls path identity and possible route continuity. Detailed schedules: [stability_axis.csv](results/stability_axis.csv); invariance data: [persistency_schedule_invariance.csv](results/persistency_schedule_invariance.csv).

### Persistency by skeleton class

N=92 node count in all classes; ten seeds per persistency value, life=.5, stability=.8. Candidate frames: line p=1, ladder p=.9, geodesic p=.5; 3,000 candidates each; p chosen to ensure connected candidate pools. Retention is the fraction of adjacent-up-frame pairs whose IDs/routes match.

| Skeleton | Distinct up-route groups in candidates | Mean ID retention at persistency 0/.25/.5/.75/1 | Mean assembled route retention at persistency 0/.25/.5/.75/1 |
|---|---:|---|---|
| Line (single S–R path) | 1 | 0/.266/.530/.781/1 | 1/1/1/1/1 |
| Ladder | 1,535 | 0/.266/.530/.781/1 | 0/.266/.530/.781/1 |
| Frequency-3 geodesic | 2,038 | 0/.266/.530/.781/1 | 0/.266/.530/.781/1 |

On the single-path line persistency changes path IDs but has no route-identity effect because there is only one shortest-path group. On ladder/geodesic candidate sets, route retention tracks path-ID retention in this probe. Counts are sampled distinct shortest paths, not a theoretical path count nor a direct exact-count control. Full seed rows: [persistency_skeletons.csv](results/persistency_skeletons.csv).

### Random links, number of paths, and MPC

In [the rebased frame sampler](YaDyGaGa/yadygaga/frameGenerator.py#L20-L51), every candidate frame loops across the skeleton edge list and includes each edge if a fresh `rng.random() < p_edge` succeeds. There is no cross-frame per-edge state or transition-duration memory: edge states are independent Bernoulli draws across frames. Therefore random-link fraction is fixed only as an expectation (`p_edge`), not controlled per realized frame, and per-link lifetime is not controlled. Both axes remain **not usable**. The Edge-Markovian alternative remains design-only in the A0-R report; Beta axes needing it are independent per-link random-link fraction and mean lifetime, with S–R uptime becoming an output rather than an enforced quota.

Observed distinct sampled S–R shortest-path groups were line 1, ladder 1,535, geodesic 2,038 under the candidate distributions above. The API groups by actual shortest path; it has no exact path-count parameter. Source/docs expose no stated hard maximum number of tracked pairs. At N=92, two-pair MPC completed for both disjoint and shared-source pair sets: four statuses were sampled and represented in the 120-frame assembled outputs; per-pair up/down candidate pool counts are in `rebased_axis_summary.json`. Demonstrated maximum: 2 pairs; documented maximum: none stated. This does not claim arbitrary pair counts are validated.

## Per-axis disposition and authorization

| Axis | A0/A0-R2 disposition |
|---|---|
| Path life | Usable on patched copy within exact-feasible range; frozen fidelity passed |
| Seed diversity | Usable on patched copy for tested feasible cells; original A0 failure remains historical |
| Stability | Partly usable: clear run-structure effect, but shares run-count formula with life and exact requests can be infeasible |
| Persistency | Partly usable: controls path-ID retention; route effect depends on skeleton having multiple path groups |
| Random-link fraction | Not usable as a controlled realized fraction |
| Random-link lifetime | Not usable; no cross-frame edge-state memory |
| Number of paths | Partly usable: shortest-path groups are observed/selected, but exact count is not a generator control |

This is the exact qualified A0 verdict entered in `alpha/gates.md`: path life and seed diversity usable on patched copy; stability and persistency partly usable; random-link fraction and lifetime not usable. Per the user's authorization, **A1 graph-family work with no generator modification and no ns-3 is authorized after this entry; it was not started here. A2 remains blocked until the user approves the post hoc normalized-diversity criterion.**

## Reproduction commands and artifact hashes

Environment: Python 3.14.4, `/home/hledirach/Documents/J2/.venv/bin/python`. Commands run after preregistration:

- `/home/hledirach/Documents/J2/.venv/bin/python /home/hledirach/Documents/J2/simple-graph-experiments-v2/alpha/A0R2/measure_sampler.py`
- `/home/hledirach/Documents/J2/.venv/bin/python /home/hledirach/Documents/J2/simple-graph-experiments-v2/alpha/A0R2/run_rebased_checks.py`
- `/home/hledirach/Documents/J2/.venv/bin/python /home/hledirach/Documents/J2/simple-graph-experiments-v2/alpha/A0R2/measure_infeasible.py`
- Rebase applicability check: `git -C /home/hledirach/Documents/YaDyGaGa apply --check /home/hledirach/Documents/J2/simple-graph-experiments-v2/alpha/A0R/yadygaga_a0r.patch` (expected conflict at timelineBlockGenerator.py:55; resolved by the explicit selectable modes in the isolated copy).

| Artifact | SHA-256 |
|---|---|
| `results/sampler_cells.csv` (initial sampler) | `86cb599d386c4c22bd62c862dc9d5320dcc787d50f1d5c8f35b9afbd918ec3bb` |
| `results/sampler_draws.csv` (initial sampler) | `fb5166a77eb459d67c008512ced5fbb9b9881d908ccbae25dce54af8aaf4dc15` |
| `results/sampler_uniform_cells.csv` | `bb3002c44b3fba888c99db8638309a2063aaa063b8d94b830bdf2c418bbe2473` |
| `results/sampler_uniform_draws.csv` | `c7dc1438ec100161f30f8c109624844f8eab9f101c71d02ca33b8f4b06ffb50b` |
| `results/sampler_uniform_summary.json` | `ad7fb27a3ad84047d3e2edf1d05e553294f862b40d4dc9e42fceb432adb82ae7` |
| `results/small_frames_bruteforce_uniform.csv` | `cf5d724daed62ff0c30680829dc9d5320dcc787d50f1d5c8f35b9afbd918ec3bb` |
| `results/infeasibility_map.csv` | `06c8fab15f32c45c02512020ff6640287a129b2861ff957ad034c1b31aed5c72` |
| `results/frozen_a0_rebased.csv` | `5cde74cc0cc9f00f3a2105f5fd035287745d4ebd2f9d9c51b7dad5fd9cecedaa` |
| `results/stability_axis.csv` | `98a32ea54afe80e6c7ebe996493ee143d37551100c674dbcc8acdd562e3cb425` |
| `results/persistency_skeletons.csv` | `b326684dcc56ea268c69061dff47b5c961deac054785909b2c55f23025acb9c5` |
| `results/persistency_schedule_invariance.csv` | `27d605af6f4712c5643d34c55b4118a44179adf2c63325590fe7048de13fc9b2` |
| `results/infeasibility_map.json` | `842a7b9c4e3503f8bc982fc3dd53beda79094ac047abf49584a689efc470a14a` |
| `results/rebased_axis_summary.json` | `188e316cfa83d31c46246a94f9ce01be15a62f17391d4db80c76765633402b47` |

## Decisions requested

1. Approve or reject the post hoc A2 normalized-diversity rule $\text{mean }D\ge.30$ plus at least five unique schedules; A2 is blocked pending this decision.
2. Review the rebase resolution (legacy selectable mode plus exact-uniform patched mode) before any upstream adoption. A1 authorization is limited to graph-family work without generator edits or ns-3.
3. Confirm whether Beta should be restricted to the exact safe-region inequality $K\le D+1$ at every selected life/stability/frame cell; this report recommends yes.

Protocol variants: **0**.
