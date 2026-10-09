# Phase 6 report — diagnosis and corrected analysis

## Scope and guardrails

Phase 6 follows the user’s gated order: diagnose first, correct metrics/baseline/statistics second, and consider only a reduced simulation set after gates. Original campaign outputs and `simple-graph-experiments-v2/phase1`–`phase5` remain unchanged. Phase 6 artifacts are under this directory. This report makes no protocol ranking. Per-realization observations and sample SD ($ddof=1$) are used; replay epochs are not treated as independent graph realizations. No Phase 6F simulation batch was run. Work stops here pending approval.

## Summary of gate outcomes

| Hypothesis / gate | Classification | Main evidence |
|---|---|---|
| H1 buffering / delayed delivery | Undecided | AODV usable-down receives were rare; delay >1 s passed the preregistered threshold in only one of three settings. Report the two conditions separately. |
| H2 oracle/window/threshold mismatch | Supported | Interpolated usable uptime materially changes the oracle and reduces/removes positive raw-PDR gaps in all three 6A settings. |
| H3 duplicate receive counting | Refuted | No duplicate sequence receives; sink callbacks matched unique sequences in the instrumented runs. |
| H4 static-baseline transition losses | Supported | 81.90% of static unrecovered packets were sent in usable intervals; 83.44% of those fell within the first second of an up-interval. |
| 6B static-baseline validation | All-up PDR criterion met with an input deviation; dynamic matching criterion failed | Both all-up results are `static` protocol rows. The hand-authored line trace has 70 rather than preregistered 60 matrices; the controls used fps 0.25 and zero warm-up, unlike dynamic comparisons at fps 1 and 45 s warm-up. |
| H5 S–R timeline diversity | Confirmed | Across 225 traces / 45 cells, each cell had one unique S–R timeline; pairwise Hamming distance was zero. Same-seed cross-topology timelines were identical in all available comparisons. |
| 6D(a) export discrepancy | Explained; documented | Zero edge mismatches; difference is equal-length shortest-path tie-breaking from graph/node insertion order vs serialized sorted-label order. |
| 6D(b) DSDV anomaly | Excluded / unresolved | Replay/control evidence points to an anomaly specific to the trace-replay setup, but the control propagation model differs; no causal clearance. DSDV remains excluded. |
| H6 stability/persistency confounding | Undecided; exploratory analysis completed | Stability slope attenuation after adding mean up-run was highly topology/protocol dependent. No confirmatory threshold was preregistered for H6, and low effective timeline sample size limits inference. |

## 6A — corrected oracle and packet evidence

The 6A batch contained 15 ns-3 invocations (three conditions × five stored realizations), each running OLSR, AODV, and static variants: 45 protocol replay variants total. The preregistered path-life 0.5 condition uses the `stability_0.0000` trace; the earlier ≈0.6644 value referred to a different path-persistency trace, not the preregistered 6A trace. Canonical Python recomputation and the C++ usable-oracle cross-check agreed.

| Condition | Raw 60-frame uptime | Traffic-window binary uptime | Traffic-window usable uptime (mean ± sample SD) | AODV PDR (mean ± sample SD) | AODV − usable uptime |
|---|---:|---:|---:|---:|---:|
| path life 0.5 / stability 0.0 | 0.5000 | 0.4907 | 0.9519 ± 0.0071 | 0.9072 ± 0.0109 | −0.0447 |
| path life 0.7 / stability 0.8 | 0.7000 | 0.6944 | 0.8618 ± 0.0087 | 0.9350 ± 0.0247 | 0.0732 |
| path life 0.9 / stability 0.8 | 0.9000 | 0.8981 | 0.9929 ± 0.0000 | 0.9833 ± 0.0000 | −0.0096 |

H2 is supported: the corrected effective uptime changes materially from the all-frame quota and removes the apparent positive AODV-minus-oracle gap in each tested cell. The raw binary-frame measure is retained for comparison, not treated as the corrected usable-channel oracle.

**H1 evidence:** pooled AODV unique receives = 5,086. Of those, 1,366 (26.86%) arrived during binary-frame-down intervals, 2 (0.0393%) during usable-down intervals, 402 (7.90%) had delay >1 s, and 244 (4.80%) had delay >2 s. By condition, delay >1 s was 4.04%, 19.96%, and 0%; the usable-down fraction did not independently meet the support rule in two settings. H1 is therefore **undecided**, not supported by combining binary-down and delay into a post-hoc union. Binary-down evidence is reported separately because that state does not equal operational usable-down.

The corrected deadline-PDR tables report the requested 0.5 s, 1 s, and 2 s metrics. AODV results (mean ± sample SD across five realizations) are:

| Condition | 0.5 s deadline | 1 s deadline | 2 s deadline |
|---|---:|---:|---:|
| path life 0.5 / stability 0.0 | 0.7378 ± 0.0136 | 0.8706 ± 0.0109 | 0.8856 ± 0.0080 |
| path life 0.7 / stability 0.8 | 0.6872 ± 0.0358 | 0.7483 ± 0.0332 | 0.8211 ± 0.0164 |
| path life 0.9 / stability 0.8 | 0.9556 ± 0.0020 | 0.9833 ± 0.0000 | 0.9833 ± 0.0000 |

The 6A realization table also contains per-packet delay means/medians and unique receive counts. The 6E summary includes deadline-PDR means, medians, sample SD, and per-realization values for all three deadlines.

**H3 evidence:** zero duplicates in all checked protocol/condition combinations; callback receive counts equaled unique sequence counts. H3 is refuted.

**H4 evidence:** 1,983 static unrecovered offered packets; 1,624 (81.90%) were sent during operational usable intervals. Of those, 1,355 (83.44%) occurred in the first second of a usable up-interval. H4 is supported. These are measured transition-associated losses, but they do not validate static as an ideal ceiling.

## 6B — static-baseline ceiling gate

The all-up line and ladder controls each achieved **static-protocol** PDR 1.000; the line row records 1,684 application packets offered and 1,684 delivered. The PDR is not an OLSR or DSDV result. The three dynamic usable-route PDRs are also static-protocol results, approximately 0.369, 0.661, and 0.869, against usable effective uptime of approximately 0.949, 0.868, and 0.993. The dynamic matching criterion failed.

Execution addendum: the hand-authored [all-up line input](6B/all_up_line.csv) contains 70 repeated matrices rather than the preregistered 60. Its provenance is a direct file-authoring operation; it was not produced by the Phase 5 graph/export pipeline and therefore does not test that serialization path. The run used `fps=0.25`, `warmup=0`, and `warmupMode=first`; it applied 70 frames over timestamps 0–276 s (276 s trace span). The dynamic usable-route runs used `fps=1`, `warmup=45`, and 60 source frames, with traffic from 45.1 to 104.0 s (58.9 s). Thus the line control's numeric all-up PDR threshold was met, but it is not an exact 60-frame replication and was not run under the dynamic comparison's timing settings. The record does not explain why 70 matrices were authored instead of 60.

## 6C — S–R timeline diversity

The read-only audit covered 225 Phase 5 traces across 45 cells, five graph seeds per cell. Each cell contained exactly one unique serialized S–R timeline and mean pairwise Hamming distance 0. All 225 available same-seed cross-topology comparisons were identical. Across cells, pooled within-timeline up-run-length variance ranged from 0 to 0.2632 frames², and pooled outage-start-position variance ranged from 0 to 325.658 frames². In contrast, across-realization variance of each realization’s mean up-run length and mean outage-start position was exactly zero in every cell, because the sequences were identical. The measured effective S–R timeline sample size is therefore one per parameter cell, despite five generator-seed labels. No generator change was made; any seed/generator redesign requires separate approval.

## 6D — diagnosed defects

### (a) Generator/export route-property mismatch

The discrepancy reproduced: generator-side retention 0.8510638 and 7 route changes versus serialized-label-order retention 0.7446809 and 12 changes. Comparing edges frame by frame yielded zero mismatching edges across all 60 frames. Six frames select different equal-length shortest routes because NetworkX tie-breaking follows in-memory insertion order before export, while the audit recomputation follows sorted serialized node labels. This is a route-property computation/tie-order discrepancy, not corrupted edge export. It is documented; no generator change was made.

### (b) DSDV warm-up/outage investigation

Ten focused runs were performed: five warm-up values (0/30/45/60/90 s) in replay mode and the same five in a plain fixed-topology control. Replay PDRs were 0.758, 1.000, 1.000, 0.747, 1.000; the plain controls all yielded 1.000. At 60 s warm-up, replay showed an Rx gap from 75.011 to 90.126 s while sampled routes retained the source route; sequence advanced from 10 to 12 near onset. No application IP no-route, route-error, MAC queue, or MAC Tx drops explained the gap; 337 PHY Rx drops were recorded. The plain fixed-topology control used a range-loss channel rather than the replay trace propagation model, so it does not isolate propagation/replay causally. ns-3 defaults were verified: PeriodicUpdateInterval 15 s, SettlingTime 5 s, Holdtimes 3 (45 s multiplier), EnableWST true. DSDV is not cleared for the reduced study and remains excluded; no “known issue” label is used as explanation.

## 6E — corrected Phase 5 statistics and H6

The analyzer reads the 225 serialized traces and replay results, averages the five replay epochs within each DG realization, then calculates between-realization results. It emits means, medians, sample SD ($ddof=1$), deterministic paired-bootstrap 95% intervals, per-realization strip plots, protocol-minus-protocol paired differences, PDR normalized to static reference, measured-feature regressions, a stability/persistency adjustment, ladder AODV realization tables, and delay-aware 6A summaries. DSDV is excluded from Phase 5 statistics because it was not part of that campaign and remains uncleared. Zero static denominators produce NaN normalized values rather than division errors. Non-finite trace features are excluded from the corresponding regression; line-topology path-identity retention is undefined and therefore has no fitted coefficient.

**H6 prediction:** stability and persistency effects are confounded with up-run structure. The original Phase 6 request specifies the measured-feature regression and asks how much stability effect disappears after conditioning on mean up-run, but gives no confirmatory decision threshold for H6. Accordingly, H6 is **undecided**; the following slopes are exploratory descriptions, not a post-hoc support/refutation test. Since there are only five distinct stability values and the same S–R timeline repeats across the five DG seeds in each cell, these regressions do not constitute independent-trace causal inference.

Stability slope change after adding measured mean up-run:

| Topology | Protocol | Unadjusted stability slope | Adjusted slope | Signed attenuation |
|---|---|---:|---:|---:|
| line | OLSR | −0.2737 | −0.2126 | 22.3% |
| line | AODV | −0.2280 | −0.0239 | 89.5% |
| line | static | 0.1250 | 0.1302 | −4.2% |
| ladder | OLSR | −0.0471 | 0.0035 | 107.5% (sign reversal) |
| ladder | AODV | 0.0490 | −0.1001 | 304.4% (sign reversal) |
| ladder | static | 0.0991 | 0.1000 | −1.0% |
| two-lines | OLSR | −0.1112 | −0.1884 | −69.5% |
| two-lines | AODV | −0.1048 | −0.0239 | 77.2% |
| two-lines | static | 0.1144 | 0.1243 | −8.6% |

Negative attenuation means adjustment increased the slope magnitude. Attenuation above 100% indicates sign reversal, not “more than all effect explained.” For path-persistency sweeps, mean up-run is constant within each topology in the serialized traces, so adding it does not change the persistency slope; the estimate cannot distinguish persistency from other sweep-linked changes.

The Phase 5 ladder AODV path-life PDR cell at 0.7 had mean 0.5691, median 0.6778, sample SD 0.2490, bootstrap CI [0.3458, 0.6980], and realization PDRs 0.6350, 0.6778, 0.7139, 0.1267, 0.6922. At 0.9, mean 0.7039, median 0.8111, sample SD 0.2646, CI [0.4658, 0.8474], with realization PDRs 0.8122, 0.2356, 0.7778, 0.8111, 0.8828. The low outcomes are not explained by a single measured feature: at path-life 0.7 the low-PDR graph had usable uptime 0.9787 (the highest in that cell), mean up-run 4.667 s, 16 transitions, path retention 0.788, frame 0 connected. At 0.9 the low-PDR graph had usable uptime 0.9929 (equal across cell), mean up-run 7.714 s, 12 transitions, path retention 0.702, frame 0 connected. The spread is therefore not attributable simply to lower usable uptime or frame-0 disconnection. Five realizations do not establish a bimodal distribution; the term “two modes” remains descriptive of the conspicuous low-vs-high points only, not a statistically validated mixture.

## Earlier results invalid or requiring re-read

- Phase 5’s all-frame binary quota should not be substituted for operational traffic-window usable uptime. Any comparison treating that value as the effective connected traffic fraction must be re-read.
- The initial path-life-0.5/stability-0.0 oracle value of ≈0.6644 came from a different path-persistency trace. The preregistered 6A trace’s corrected usable uptime is ≈0.9519.
- Phase 5’s report describes a population SD in its methods despite the present requirement for sample SD. Its means remain historical, but spread/uncertainty and any inferential reading must be recomputed from the new per-realization tables.
- Static is not a ceiling; all ceiling language and such interpretation must be removed from prior analyses.
- Phase 5 treats five graph seeds as five S–R timeline realizations; this overstates effective timeline sample size. Per-cell connectivity timelines are identical.
- Generator-side and serialized path-retention/route-change values are not directly comparable without fixing the node iteration/tie-breaking order. Edge traces themselves match.
- DSDV’s 60 s warm-up result must not be treated as a generally characterized protocol result; the replay/control model mismatch leaves causality unresolved.
- Any Phase 5 protocol interpretation should be re-read with epoch averaging nested inside DG realization, paired realization differences, corrected traffic-window metrics, and the displayed individual realization values.

## Code, tests, provenance, and commands

Changed/added analysis code and metrics are in Phase 6 or the shared metric/test files: [corrected oracle metrics](../../oracle_metrics.py), [oracle tests](../../tests/test_oracle_metrics.py), [6A analyzer](6A/analyze_6a_corrected.py), [6C timeline audit](6C/analyze_timeline_diversity.py), [6D export audit](6D/audit_export_mismatch.py), [6D DSDV analysis](6D/analyze_dsdv.py), and [6E analyzer](6E/analyze_phase5_corrected.py). The external ns-3 scenario gained opt-in `--staticOracleMode=frame|usable` with default `frame`; the separate DSDV control source was added outside this workspace. Legacy deterministic CSV regressions passed with diagnostics both disabled and enabled (timing columns excluded). Final Python test discovery: 8 tests passed.

### Simulation commands and run counts

The 6A batch was exactly 15 `graph-run` invocations (three conditions × five realizations), with three routing variants per invocation (45 variants). From `/home/hledirach/Documents/sp1-sp2`, each invocation used this exact argument form; the 15 concrete `framesCsv`, `outDir`, and seed values are enumerated in the [6A run manifest](6A/run_manifest.json):

```sh
./ns3 run "graph-run --framesCsv=<manifest Phase 5 frame path> --outDir=<phase6/6A/runs condition/graph path> --routing=olsr,aodv,static --flows=S:R --dataRate=50kbps --packetSize=1024 --lossThresholdDb=150 --interpolate=true --defaultLossDb=1e6 --txPowerDbm=20 --linkUpLossDb=10 --linkDownLossDb=125 --fps=1 --seed=<42,47,52,57,62 by graph> --warmup=45 --warmupMode=first --dumpRoutes=true"
```

The exact 6B five-run command list and flags are frozen in the [6B preregistration](6B/static_baseline_preregistration.md). The DSDV gate ran ten invocations (five replay and five plain-control warm-ups); the exact design, warm-up list, source configuration, and measured timing are recorded in the [6D DSDV preregistration](6D/dsdv_investigation_preregistration.md). The export-mismatch reproduction is the deterministic offline script [audit_export_mismatch.py](6D/audit_export_mismatch.py); no ns-3 simulation was needed for that comparison.

The final offline analysis was run with `/home/hledirach/Documents/J2/.venv/bin/python /home/hledirach/Documents/J2/simple-graph-experiments-v2/phase6/6E/analyze_phase5_corrected.py`. It was run twice with identical SHA-256 digests for all generated CSV tables. It did not invoke ns-3. The 6E [analysis config](6E/config.json) records analysis script hashes, inputs/design, and generated table hashes. Historical simulation configs and run-manifest hashes were not overwritten.

| Artifact | SHA-256 |
|---|---|
| [6E analysis script](6E/analyze_phase5_corrected.py) | `74527074df365d7530c318f23222c94448e8c13b1436c25f4f3e93265e09e201` |
| [Per-realization features and PDR](6E/phase5_realization_features_pdr.csv) | `659e8bfc5435d64d74a77be786db798680a54cb4560a423efcd0be3add56f868` |
| [Cell statistics](6E/phase5_cell_statistics.csv) | `572600d37fe84bc169debc5212a62662d1bb835cec6ee4131cf85bdc04445db6` |
| [Paired realization differences](6E/phase5_paired_differences.csv) | `305c5bdf9861707ec7f520cf8c6ddabd1971fa282d3ffad429400646d9abd97a` |
| [Measured-feature regressions](6E/phase5_feature_regressions.csv) | `04d8f46dca6cf6d2ec58bace176dd4421df4d836777bc28f9c1de0002ed57d02` |
| [Parameter/run-length adjustment](6E/phase5_parameter_runlength_adjustment.csv) | `ecdf885d68d17f9e9ed6768f1038524a0ed5cf53e7ef14f053cc953075a59bfe` |
| [Ladder AODV realization spread](6E/ladder_aodv_spread.csv) | `340193b5b78637b0f3e9f56bd213d231ddf037d43ca9c71b928fcd802afc0021` |
| [6A deadline-PDR summary](6E/phase6a_deadline_pdr_summary.csv) | `dcc10a96af359c4eff823fbfab44ffdc77e06db3f1345a9a2eb40c16529f2748` |

Additional outputs: [ladder AODV per-cell table](6E/ladder_aodv_modes.csv), [line strip plot](6E/strip_pdr_line.png), [ladder strip plot](6E/strip_pdr_ladder.png), and [two-lines strip plot](6E/strip_pdr_two-lines.png).

Per-run measured wall time and exact counts for completed simulation batches are preserved in the Phase 6A–6D configs/logs. The full 6F design as preregistered would be 2,400 `graph-run` invocations, each containing three routing variants, or 7,200 protocol replay variants. The global cap is stated as 2,500 “ns-3 runs” without specifying whether it counts invocations or protocol variants; the design is below the cap under the former interpretation and exceeds it under the latter. In addition, no measured run at the maximum 960-frame / 4-fps trace duration is available, so the earlier 60-frame runtime is not a defensible per-run estimate for this campaign. No 6F batch was launched and no runtime estimate was logged; resolving cap accounting and obtaining a comparable measured runtime are prerequisites to a compliant 6F estimate. Historical run manifests/hashes were not overwritten.

## Not done and possible Phase 7 work

- No Phase 6F rho-axis or replicated path-life/stability simulations were run. The static-ceiling gate failed; H1 remains undecided; DSDV remains excluded; the 6C effective timeline sample size is one. The full plan is 2,400 graph-run invocations / 7,200 protocol variants. Define the cap’s counting unit and measure runtime at the planned maximum trace size before scheduling a compliant reduced campaign.
- No generator changes were made. No causal DSDV isolation was achieved. No mixture model was fit to five-point ladder AODV cells.
- Phase 7 (proposal only):
  1. Obtain approval for a redesigned timeline-diverse seed/generator scheme.
  2. Obtain approval for a validated static-baseline correction or an explicitly non-ceiling alternative reference.
  3. If approved, preregister a capped reduced experiment and exact wall-time budget before launching any simulations.
  4. If DSDV is reconsidered, first use a propagation-model-matched causal control.
