# A2f-2 result — isolated `(U,K)` timeline interface

**Gate: PASS after registered correction addendum 1.** The first grid run had an arithmetic mismatch in one preregistered cell: the formula specified the geometric midpoint for life=.7 as K=11, but the numeric cell was mistakenly entered as K=16. The original K=16 test and its artifacts are retained as a deviation and excluded from the gate. Before rerunning the corrected cell, [addendum 1](prereg_addendum1.md) was preregistered and logged. The final grid combines the 11 unaffected original cells with the corrected life=.7, K=11, 200-seed replacement; exact corrected-cell results appear below. Do not interpret the initial uncorrected table's K=16 line as a gate result. The adapter adds opt-in `behavior="uk"`; it translates explicit U/K requests to the unchanged A2d item 1/A0R2 patched sampler and makes `patched-v2` an explicit compatibility alias. Legacy and patched code were not modified. Inputs are rejected when infeasible; no implicit clamp is performed. For trivial schedules the exact supports are all-down `(U,K)=(0,0)` and all-up `(U,K)=(F,1)`.

The table is the frozen 12-cell F=120 grid, 200 seeds per cell (`42..241`). Each cell reports realized down-run counts and the registered Monte Carlo chi-square p-value (99,999 multinomial null draws; diagnostic seed 20261010). The reported p=1 for cells with one supported down-run category is uninformative by design. **Limitations applying to this table:** A2a stability-rule life and mean-up remain confounded; timeline diversity is family-independent by construction; the generator is patched and non-upstream; the A2b gate is non-binding by construction due to greedy max-min selection; Level 2 route diversity is tie-break-sensitive; time-respecting reachability permits waiting and is not an OLSR/AODV/DSDV oracle.

| life | U | K | mean up (frames) | realized down-run counts | MC p | exact U/K | max trace (s) |
|---:|---:|---:|---:|---|---:|---:|---:|
| .3 | 36 | 36 | 1.000 | 35:31, 36:104, 37:65 | .66769 | 200/200 | .000306 |
| .3 | 36 | 8 | 4.500 | 7:0, 8:33, 9:167 | .42247 | 200/200 | .000187 |
| .3 | 36 | 2 | 18.000 | 1:0, 2:10, 3:190 | .87465 | 200/200 | .000154 |
| .5 | 60 | 60 | 1.000 | 59:195, 60:5 | .56921 | 200/200 | .000278 |
| .5 | 60 | 11 | 5.455 | 10:1, 11:63, 12:136 | .11631 | 200/200 | .000187 |
| .5 | 60 | 2 | 30.000 | 1:0, 2:14, 3:186 | .79644 | 200/200 | .000327 |
| .7 | 84 | 37 | 2.270 | 36:200 | 1.000* | 200/200 | .000302 |
| .7 | 84 | 16 | 5.250 | 15:31, 16:107, 17:62 | .58103 | excluded deviation | .000248 |
| .7 | 84 | 3 | 28.000 | 2:1, 3:37, 4:162 | .43010 | 200/200 | .000191 |
| .9 | 108 | 13 | 8.308 | 12:200 | 1.000* | 200/200 | .000227 |
| .9 | 108 | 7 | 15.429 | 6:55, 7:108, 8:37 | .96179 | 200/200 | .000209 |
| .9 | 108 | 4 | 27.000 | 3:14, 4:97, 5:89 | .78540 | 200/200 | .000210 |

*Only one down-run category is supported, so goodness-of-fit is uninformative; this is not evidence of a distributional fit.* All 2,400 individual operations were below 60 seconds; maximum observed timeline-generation duration was under 0.0004 s. The 12 cell-level Monte Carlo tests were not rejected at .01.

### Corrected replacement cell (included in the final gate)

The corrected registered life=.7 cell is F=120, U=84, K=11, mean-up=7.636 frames, seeds 42..241. **Limitations applying to this correction table:** life and mean up-run remain confounded under A2a stability rule; timeline diversity is family-independent by construction; generator is patched non-upstream; A2b gate is non-binding by construction because of greedy max-min selection; Level 2 route diversity is tie-break-sensitive; time-respecting reachability permits waiting and is not an OLSR/AODV/DSDV oracle.

| life | U | K | mean up (frames) | realized down-run counts | MC p | exact U/K | max trace (s) |
|---:|---:|---:|---:|---|---:|---:|---:|
| .7 | 84 | 11 | 7.636 | 10:9, 11:86, 12:105 | .13553 | 200/200 | .000187 |

The 99,999-draw Monte Carlo test was not rejected at .01. All 200 corrected traces met exact quotas; no trace timed out or was retried. The corrected per-seed record/config hashes are stored separately under `results/correction_v1/`.

## Regression, support and error gates

| Gate | Outcome |
|---|---:|
| F=8 direct enumeration vs formula for all `(U,K)` pairs | 81/81 exact; 256/256 binary strings covered |
| `legacy` output vs original A2d item 1 generator | 15/15 exact timeline + path-ID comparisons |
| `patched-v2` output vs original A2d item 1 generator | 15/15 exact comparisons |
| `patched-v2` output vs stored A2c ER_N92_r1 output | 15/15 exact comparisons |
| `uk` output vs same-seed equivalent `patched-v2` | 15/15 exact comparisons |
| Infeasible K at Kmax+1 for all A2f-1 `(F,life)` cells | 27/27 typed fields exact; each <1 s |
| Mean-derived infeasible request (`F=120, life=.9, m=4`) | K requested 27, Kmax 13; typed fields exact; <1 s |
| Clean-copy overlay dry-run | PASS; donor hashes verified; no protected-source mutation |

All seeds, requested and realized per-trace quotas, down-run counts, operation times, configs, regression identities and exception diagnostics are retained in `results/`. Each per-trace config records timeline base seed and the established pool/assembly offsets (`+10000`, `+20000`) for reproducibility; the timeline-only tests do not run pool or assembly stages. No retry or seed search occurred.

## Artifacts and provenance

- Preregistration: `prereg.md` (hash recorded in `../gates.md`).
- Correction preregistration: `prereg_addendum1.md` (registered before the replacement run; hash in `../gates.md`). The original erroneous K=16 attempt remains in the first result files and is explicitly excluded.
- Isolated overlay: `source/yadygaga/`; original `timelineBlockGenerator.py` and `frameGenerator.py` donor hashes are frozen in `a2f-2.patch.json`.
- Patch descriptor: `a2f-2.patch.json`; clean-copy apply/dry-run helper: `apply_patch.py`.
- Registered test runner: `run_tests.py`.
- Results: `results/summary.json`, `results/grid_cells.json`, `results/grid_per_seed.jsonl`, `results/regressions.json`, `results/infeasibility.json`, and per-trace JSON configs.
- Corrected midpoint: `results/correction_v1/summary.json`, `results/correction_v1/per_seed.jsonl`, and per-seed source-hashed configs.
- This isolated A2d-derived generator is patched and non-upstream. The result demonstrates interface decoupling only; it does not relax the finite support, establish protocol performance, or authorize A3.

**Known limitations (mandatory carry-forward):** (1) life and mean up-run remain confounded under the A2a stability rule; (2) timeline diversity is family-independent by construction; (3) generator is patched non-upstream; (4) A2b gate is non-binding by construction because of greedy max-min selection; (5) Level 2 route diversity is tie-break-sensitive; (6) time-respecting reachability allows waiting and is not an OLSR/AODV/DSDV oracle. No protocol variants, ns-3, or A3.
