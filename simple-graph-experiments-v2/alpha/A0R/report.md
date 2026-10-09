# Alpha A0-R — root-cause diagnosis and isolated remediation

**Status: A0-R patched-copy generator gates pass; user review/upstream decision pending.** This is separate from the historical A0 result. A0 remains failed as recorded: **1 unique S–R bit string of 5; mean pairwise Hamming fraction 0.0.** No change was made to the A0 report or verdict. A0-R used zero protocol variants and no ns-3.

## Scope and provenance

- Registered protocol: [A0-R preregistration](prereg.md), final SHA-256 `fadc390f5491c2b997f676bb94e208982ff3d71cd0a7a140a10c11537dfcbe7c`. Its initial pre-execution draft hash, before correcting the clean-source cap statement, is separately logged in [the Alpha gate log](../gates.md).
- Source base: YaDyGaGa clean commit `51b01ac7faa78a494c3baedc560d658f384afe09`; clean Git tree object `5040cf6785fbb3a49cb48a7eb79eb7e4a19cbf9f`. The reconstructed pre-patch 49-file content-manifest hash is `bd28247d110c5ca09449e9e7ddc2bf618f95de5d41e665cfc1f2a8db2f3d2721`; patched 49-file manifest hash is `ba8d828b7b4b5ce699f55a2bfbb8c4f621a9ab4366a9f2d316d68836a7200047`.
- The deleted historical `/tmp/yadygaga-alpha-a0-clean` materialized-tree hash is unavailable and is **not** reconstructed or represented as known. The new clean baseline was independently reconstructed from the pinned Git commit under `/tmp/yadygaga-alpha-a0r-clean` before the registered diagnostics. The diagnostic manifest records its source-file hashes.
- Exact isolated patch: [yadygaga_a0r.patch](yadygaga_a0r.patch), SHA-256 `00b8774d511d52bc6765420e5837d50a67f417793bf98e3b3019974b3ff48a05`. `git apply --check` passed against the reconstructed clean baseline. Patched-source file hashes: `timelineBlockGenerator.py` `79c7db13016b6225973650ec561b343e7223b241ae0039bacacd1e810e8d04c6`; `frameGenerator.py` `e84971f89cb966a574bf447ce8135c0c241b407be14e5066db2f82f3c2ec6b4b`; `dynaGraph.py` `8e75cb59139516bfcc6ccfe672281575c4e8490fdf03d5d5bbcbef8a8b203c42`.
- Protected dirty checkout files were not changed: dirty `G2DG-SPC.py` hash remains `3231c9c6a8b4a25f3fbfd5d3eadfd0c785b45043fd90bfb3c39ba5e6f390a03b`; dirty YaDyGaGa `timelineBlockGenerator.py` remains `49506167cf764705e4e3fc7d3944d070dc2602c69b8ae250fcf3fc6e851591f5`; dirty `toolbox.py` remains `a5b977aaff8aa132d3b7c53b6609863fb6393e94a03bee239a12399ce144e485`.
- Historical A0 preregistration deduplication was criteria-neutral: hash before `05bb91d13e99081bb4cd19241c45b04231730d55134707ae0f678372b1273016`, after `da4d1c89266257cc6563f18794064698e935898c748beb5d582b6643ee31953a`. The A0 worker-wrapper hash is `eafb56abf7482f90aed77f56ea2a9e19fc198156c9fb02efc90dc3e631c6cbec`; the aggregation-only wrapper hash is `77aac3c876a7d484bfb6b232bd48d6bb9d79cdc47dc97fd0acd72ebf3186f75b`.

The clean-source facts are visible in the old side of the patch and in the source snapshot: clean `frameGenerator.py` sampled candidate edges independently and grouped up frames by shortest S–R path; clean `timelineBlockGenerator.py` reset global RNG state, rounded the up quota, mapped stability to a run count, and used deterministic evenly split block sizes and placements for ordinary multi-run cases. The clean implementation had **no** `down_count + 1` cap. In the reconstructed clean source, the relevant original locations were frame sampling lines 20–67, timeline seed/quota lines 45–52, run calculation lines 109–119, and path-ID labeling lines 246–269; SPC assembly was at `dynaGraph.py` lines 36–108. The final isolated implementation is linked here: [patched timeline generator](YaDyGaGa/yadygaga/timelineBlockGenerator.py#L30-L105), [SPC frame sampling](YaDyGaGa/yadygaga/frameGenerator.py#L20-L67), and [SPC assembly](YaDyGaGa/yadygaga/dynaGraph.py#L36-L80).

## Step 1 — root cause, in registered order

| Candidate cause | Measurement | Verdict |
|---|---|---|
| Seed does not change Boolean timeline | Direct calls to clean `SPCTimelineBlockGenerator.generate_blocks()` for seeds 42–46, N=92/120 frames/life .5/stability .8/persistency .9: all five Boolean timelines have SHA-256 `0174c911964d2b8c753230bec2bb8488f63115dbdc6a58c742a84ae7a4884e86`; exactly 1 distinct Boolean sequence; 24 transitions; uptime .5. Path-ID counts varied (15, 15, 17, 17, 18), confirming the seed affected labels but not the Boolean sequence. | **Root cause confirmed.** |
| Too few candidate-frame trials / insufficient horizon | At 500, 2,000, and 10,000 trials, five seeds each, every horizon produced 1 distinct assembled S–R bit string and mean Hamming 0.0. N=92 pools grew with trial count but remained populated. | **Not the cause.** More trials do not change a fixed Boolean schedule. |
| Stability/persistency coupling | At every stability/persistency grid cell, five seeds still produced 1 unique S–R sequence and mean Hamming 0. Stability changed the transition count (118 at 0.0, 70 at 0.4, 24 at 0.8); changing persistency among 0/.5/1 did not change Boolean bits or uptime. | Stability controls run count; persistency controls path identity, not Boolean S–R diversity. |
| Up/down pool starvation | At N=92 and N=162, p_edge=.5, all five seeds and each 500/2,000/10,000 trial setting had nonempty up/down pools; no pool was below the preregistered descriptive `<5` size label. At N=92/500, up pools held 453–469 frames across 423–431 route groups and down pools 31–47; at N=162/500, up pools held 451–472 frames across 448–471 groups and down pools 28–49. | **Not the cause at tested settings.** |

The specific clean-code failure was not “seed is ignored” globally: it was that seeded randomness was consumed only by path-ID assignment in the ordinary multi-up-run block path. Quota and stability determined the Boolean pattern, and block sizing/placement was deterministic. This matches A0’s frozen diversity failure. Increasing the frame-pool horizon or changing pathPersistency cannot repair it.

### Horizon and pool details

The per-seed data are in [horizon_trials.csv](results/horizon_trials.csv), [horizon_summary.json](results/horizon_summary.json), and [pool_validity.csv](results/pool_validity.csv). For N=92, up-frame/down-frame ranges by trial count were 453–469 / 31–47 (500), 1,816–1,849 / 151–184 (2,000), and 9,166–9,199 / 801–834 (10,000). For N=162 they were 451–472 / 28–49, 1,828–1,846 / 154–172, and 9,188–9,235 / 765–812, respectively. All 30 N=162 pool-check rows were valid. The largest 10,000-trial pool-check time was 4.342 seconds; A0's separate frozen timing threshold remains 600 seconds.

## Step 2 — feasible timeline space and stop rule

For frames $T$, rounded up quota $U=\operatorname{round}(T\cdot life)$, down quota $D=T-U$, and clean-HEAD run target $K=\operatorname{round}(1+(1-stability)(U-1))$ (clamped only to $1\ldots U$), an exact-quota timeline with exactly $K$ up-runs exists only when $K\le D+1$. For nontrivial feasible cells, the exact count is

$$\binom{U-1}{K-1}\binom{D+1}{K}.$$

The old clean code has no $D+1$ cap. Two out-of-scope grid cells per frame count are therefore infeasible: life .7 at stability 0 and .4. The clean implementation could silently truncate/pad and, for the tested 120/.7/.4 case, did not finish within a 2-second safety timeout. Those grid cells are not frozen A0 acceptance cells. All frozen fidelity cells (120 frames, lives .3/.5/.7, stability .8), the frozen diversity cell (120/.5/.8), and the timing cell (120/.5/.8) are feasible.

| Frames | Life | $K$ at stability 0 / .4 / .8 | Exact valid timeline counts, same order | Five-witness mean pairwise Hamming, same order |
|---:|---:|---|---|---|
| 60 | .3 | 18 / 11 / 4 | 608,359,048,206 / 111,864,980,579,352 / 83,918,800 | .430 / .403 / .420 |
| 60 | .5 | 30 / 18 / 7 | 31 / 10,703,696,173,750,125 / 1,249,100,716,500 | .580 / .530 / .503 |
| 60 | .7 | 42 / 26 / 9 | 0 / 0 / 8,826,555,776,610 | — / — / .400 |
| 120 | .3 | 36 / 22 / 8 | 1,244,981,450,259,157,662,259,650 / 293,278,189,642,330,420,512,372,960,000 / 323,614,239,197,792,400 | .415 / .417 / .408 |
| 120 | .5 | 60 / 36 / 13 | 61 / 1,902,870,077,593,125,142,439,497,038,077,235 / 7,350,800,972,159,737,295,248,500 | .493 / .483 / **.520** |
| 120 | .7 | 84 / 51 / 18 | 0 / 0 / 3,601,332,440,851,846,551,457,414,500 | — / — / .418 |

Counts are exact. The Hamming column gives a **constructive five-timeline witness**, not a claim that the true maximum was enumerated. A quota-only certified upper bound is .5 for life .3/.7 and .6 for life .5. This is sufficient for the stop decision: the frozen diversity cell has more than five valid schedules and an actual witness at .520, strictly above .10. The frozen fidelity cells also have valid exact-quota/run witnesses. No threshold was relaxed; the stop rule did not trigger. Full witness strings, exact bounds, counts, and per-cell labels are in [feasibility.csv](results/feasibility.csv).

## Step 3 — isolated remediation and frozen A0 rerun

Only the derived copy under `alpha/A0R/YaDyGaGa/` was patched.

- The SPC block generator samples seeded positive compositions for the exact rounded up quota and exact stability-derived up-run target, with valid boundary/run placements. It uses a local timeline RNG and a separate path-label RNG. Out-of-range life/stability values now raise `ValueError`; structurally infeasible quota/run combinations raise an explicit `ValueError` rather than truncate, pad, or hang. See [the patched timeline implementation](YaDyGaGa/yadygaga/timelineBlockGenerator.py#L30-L105).
- SPC frame sampling accepts its own `seed` and uses a local RNG; sampling remains i.i.d. on the supplied skeleton edges at `p_edge`. Assembly and unique-assembly helpers use local seeded RNGs; the SPC `buildDynaGraph` seed is independent from frame and timeline seeds. MPC timeline generation likewise uses a local RNG. See [the patched frame sampler](YaDyGaGa/yadygaga/frameGenerator.py#L20-L67) and [the patched assembly code](YaDyGaGa/yadygaga/dynaGraph.py#L36-L80).
- Clean `generateMPCFrames` was left unchanged. Regression fixture compared its output with clean HEAD for N=9, two pairs, 200 trials, p_edge=.5, seed 971; clean and patched results were byte-identical under the canonical signature (SHA-256 `de6394c29c6279793159041a352412e4ee0a99684bf24d347880643880f104e3`, 3 status patterns). This does not claim general legacy SPC trace equivalence; seeded Boolean placement intentionally changed.

| Frozen A0 gate | Patched A0-R result | Verdict |
|---|---|---|
| Diversity: N=92, 120 frames, life .5, seeds 42–46 | 5 unique S–R strings; mean pairwise normalized Hamming **0.5366667** (> .10) | **Pass** |
| Fidelity: N=92, 120 frames, lives .3/.5/.7, five seeds each | All 15 traces had exact requested up count and exact requested up-run count; max absolute S–R uptime error **0.0** (≤ .05) | **Pass** |
| Timing: N=162, 120 frames, seeds 42–44 | Max observed generation time **0.17221 s** (<600 s); every up/down pool nonempty | **Pass** |

Detailed seeded runs and hashes are in [patched_a0_gate_results.csv](results/patched_a0_gate_results.csv) and [patched_a0_gate_summary.json](results/patched_a0_gate_summary.json). Timing values are measurements, not new thresholds.

## Step 4 — remaining capabilities and gaps

### MPC

At N=92, 1,000 sampled frames, p_edge=.5, independent 120-frame pair timelines (life .5, stability .8), both disjoint pairs `(Node_0,Node_31),(Node_1,Node_91)` and shared-source pairs `(Node_0,Node_31),(Node_0,Node_1)` produced all four joint reachability status patterns and assembled 120 frames. Disjoint sample counts by status `(TT,FT,TF,FF)` were `(866,86,40,8)`; shared-source counts were `(887,49,19,45)`. This demonstrates the two-pair cases, not a maximum supported pair count. Full inputs and per-pair pools are in [remaining_capabilities.json](results/remaining_capabilities.json).

### Invalid and infeasible requests

Clean HEAD returned all-down/all-up traces for path_life -0.1/1.1, and returned timelines for stability -0.2/1.2 instead of rejecting out-of-range inputs. A0-R now rejects all four with `ValueError`. For the in-range but structurally impossible 120-frame life .7/stability .4 request, clean HEAD exceeded the 2-second safety timeout; A0-R raises `ValueError` stating `up_count=84, up_runs=51, down_count=36`. No request is silently repaired in the patched SPC API.

### Edge-Markovian fallback — design only

The current candidate sampler independently samples each skeleton edge per frame; it has no per-link persistence/lifetime control. A possible future two-state edge model would use stationary random-link fraction $\pi$ and mean up duration $L$ frames, for $0<\pi<1$:

$$p_{10}=1/L,\qquad p_{01}=\frac{\pi p_{10}}{1-\pi}=\frac{\pi}{L(1-\pi)}.$$

Parameters must keep both transition probabilities in $[0,1]$; endpoint fractions 0 and 1 are absorbing special cases. This model would make S–R uptime an output rather than an enforced quota and would confound edge dynamics with topology unless $\pi$ is calibrated per graph family. It was not implemented or used for A0-R.

### Phase 7D generator_v2 classification

Phase 7D `generator_v2.py` is a **separate replacement/offline timeline generator**, not a YaDyGaGa wrapper or fallback: its versioned stream semantics, graph-pool format, and validation path are independent, and the validator does not import YaDyGaGa. Its cited validation scope is N=5/8 with 60-frame traces. It is not evidence for the A0 N=92/162 gates and was not used here. See [Phase 7D validation summary](../../phase7/phase7_report.md#L82), [the standalone v2 module](../../phase7/7D/generator_v2.py#L1-L10), and [the Alpha gate history](../gates.md).

## Commands and artifact hashes

Commands executed from the J2 workspace using `/home/hledirach/Documents/J2/.venv/bin/python`:

- `python simple-graph-experiments-v2/alpha/A0R/diagnose_a0r.py` — clean-HEAD ordered diagnosis and feasibility.
- `python simple-graph-experiments-v2/alpha/A0R/run_a0r_gates.py` — patched frozen A0 reruns and clean-MPC regression.
- `python simple-graph-experiments-v2/alpha/A0R/probe_a0r_remaining.py` — MPC and invalid/infeasible request probes.

SHA-256 of generated data artifacts:

| Artifact | SHA-256 |
|---|---|
| `results/diagnostic_manifest.json` | `a7e21997ccab9239df78d33133e5130219e1a5d21b069203188ba4fac157333c` |
| `results/direct_timeline_seeds.csv` | `08f9494331f1fd30701ffce0604f35f09f07167ed5679477e4cd433923d9af69` |
| `results/horizon_trials.csv` | `30991b1aba614a7a9aecef8ff72255ce322c4483f5a23c7154b694447b46f6be` |
| `results/horizon_summary.json` | `1c7279ef876de6ea6901f8965b07b4e6b90daaf4d1ab80d6eab0cb358f0ad9f1` |
| `results/parameter_coupling.csv` | `5be57238f5f07d08f4ea6cb434073d1783685c1ee5a2c85b10a7da51c694f461` |
| `results/pool_validity.csv` | `fa8cfd22659c8b474ba213eeb27c2eb799d9348a16b179428badbfb997ef45a1` |
| `results/feasibility.csv` | `b4385df9ff0e9aa0b16073b21f1ef10952e6321af416464bd253a78923fa353b` |
| `results/patched_a0_gate_results.csv` | `4b07938bc2906ec2fbe201c4fb8b2575e69e663ed706d9ea37d056d20aeff092` |
| `results/patched_a0_gate_summary.json` | `52799d732db7bd8974803e18e8168dc94b24283cabedbeac51db05e99d41b14e` |
| `results/remaining_capabilities.json` | `061e06d4b93d8468554f903aa5fb8b3e711c6d11cb9d128a0fb4c8fdbaccb913` |

## Decision boundary

A0-R establishes that the diversity failure was remediable in a derived copy without changing A0 thresholds, and that the patched copy passes the frozen A0 gates. **This does not retroactively pass A0 or authorize upstream replacement.** User decision requested: whether to accept/review the exact patch for upstreaming or retain it as an isolated experiment. A1 and Beta remain blocked until explicitly authorized; protocol-variant count remains zero.
