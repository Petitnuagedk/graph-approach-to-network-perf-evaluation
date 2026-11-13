# A2f-3 result — generator-only life/run-duration decoupling

**Gate: PASS.** The preregistered 300 isolated trace operations completed successfully within the 60-second per-operation limit; there were no timeouts, retries, or substitutions. All requested and realized U/K values matched, every per-frame S–R connectivity bit matched the Boolean timeline, life errors were zero, all 300 shortcut fractions were exactly zero, and every assembled edge was a subset of its A1 skeleton. The registered common-support grid passed the average-tie Spearman gate: `rho(life, mean-up)=-0.0990867` (absolute value .0991 <= .30). The A2a stability-rule comparator produced `rho=+1.0`.

The main table aggregates 25 traces per `(life,target)` cell (five A1 families × the five A2b-selected seeds for that life). These values are descriptive, not independent statistical replicates: timelines are family-independent by construction, and the same A2b seeds recur at each duration class. The table's `store-carry-forward` column follows the frozen wait-permitted temporal reachability definition; it can exceed requested life, so the difference `life - reachability` can be negative. **Limitations applying to this table:** life and mean up-run remain confounded under the A2a stability rule; timeline diversity is family-independent by construction; the generator is patched non-upstream; the A2b gate is non-binding by construction due to greedy max-min selection; Level 2 route diversity is tie-break-sensitive; time-respecting reachability permits waiting and is not an OLSR/AODV/DSDV oracle.

| life | target class | K by life | realized mean up (frames) | mean transitions | instant S–R uptime | shortcut | store-carry-forward reach (mean ± sample SD) |
|---:|---|---:|---:|---:|---:|---:|---:|
| .3 | shortest common | 4 | 9.000 | 8.0 | .300 | 0 | .9273 ± .0344 |
| .3 | geometric midpoint | 3 | 12.000 | 6.0 | .300 | 0 | .9223 ± .0391 |
| .3 | longest common, cap 30 | 2 | 18.000 | 4.0 | .300 | 0 | .9217 ± .0364 |
| .5 | shortest common | 7 | 8.571 | 13.4 | .500 | 0 | .9337 ± .0365 |
| .5 | geometric midpoint | 5 | 12.000 | 9.8 | .500 | 0 | .9297 ± .0317 |
| .5 | longest common, cap 30 | 4 | 15.000 | 8.0 | .500 | 0 | .9270 ± .0333 |
| .7 | shortest common | 10 | 8.400 | 19.6 | .700 | 0 | .9357 ± .0334 |
| .7 | geometric midpoint | 7 | 12.000 | 13.8 | .700 | 0 | .9297 ± .0304 |
| .7 | longest common, cap 30 | 5 | 16.800 | 9.8 | .700 | 0 | .9300 ± .0325 |
| .9 | shortest common | 13 | 8.308 | 24.0 | .900 | 0 | .9370 ± .0322 |
| .9 | geometric midpoint | 9 | 12.000 | 16.6 | .900 | 0 | .9317 ± .0366 |
| .9 | longest common, cap 30 | 6 | 18.000 | 11.4 | .900 | 0 | .9330 ± .0355 |

The correlation was computed on the 12 unique planned `(life,mean-up)` design centers only; the five seeds and five graph families were not counted as additional correlation units. A2a `K` values were `{26,30,26,12}` at lives `{.3,.5,.7,.9}`, with mean up-run frames `{1.3846,2.0000,3.2308,9.0000}` and Spearman `+1.0`. The UK grid used the common feasible duration interval, not a separate per-life minimum: common lower bound `108/13=8.3077`, geometric target `12.2286`, and common maximum `18` under a 30-frame cap. This truncation is forced by A2f-1's exact-quota supports; 30 frames is a cap, not a common attainable value. Actual feasible K and mean-up values are listed in the table.

## A2f-3 gate checks

| Check | Result |
|---|---:|
| Registered trace operations | 300/300 success; no missing cells |
| Exact requested/realized U and K | 300/300 |
| Instant S–R mask equals Boolean timeline | 300/300; zero disagreements |
| Requested-life error <= .05 | 300/300; observed error 0 |
| Shortcut fraction exactly zero | 300/300 |
| All frame edges contained in A1 skeleton | 300/300 |
| UK Spearman absolute value <= .30 | 0.0991 <= .30, PASS |
| A2a comparator Spearman | +1.0 |
| Temporal reachability | descriptive `store-carry-forward`; no pass threshold |

Per-frame route connectivity, hop counts, canonical and NetworkX route sequences, edge fingerprints, and complete assembled edge lists are saved with each trace. Per-trace outputs include exact bit schedules and path IDs, source hashes, all three deterministic seed values, frame pool counts, observed up-run lengths, transitions, instantaneous S–R status, shortcut flags, and temporal reachability. Numeric cell SDs use `ddof=1`.

## Provenance and artifacts

- Preregistration: [prereg.md](prereg.md), SHA-256 `b423370340c38840d403941a86f46dc9f78dbd8064bcff76c3928a86b8f4b477`.
- Runner: [run_study.py](run_study.py), SHA-256 `438f7c7e5ebfb19d39b5cfa7f317d80065c2c92824829c68db04dcfbd8c69ceb`.
- Output manifest writer: [write_manifest.py](write_manifest.py), SHA-256 `2d3721008a65650c8abef551fbc5be45e22d22170b1b974d2f2f95fb984adcba`.
- Summary: [results/summary.json](results/summary.json), SHA-256 `d4e8542298c94bc616bbe5b201f630220c2144c917214c281179726dfe08592e`.
- Correlations: [results/spearman.json](results/spearman.json), SHA-256 `f4668402262ac25069c3eaed3ad37d230de5f1fba45f1cc242542771882465e9`.
- Per-trace table: [results/per_trace.csv](results/per_trace.csv), SHA-256 `3e45e6709e0d391568de846198600f063f2c90a154935128d4e821fab7fb86f3`.
- Family/life/duration summary: [results/cell_summary.csv](results/cell_summary.csv), SHA-256 `0fc66c78931f6f4795ad8109272092fe018cf4618b57bc7b86c46a838f4f6643`.
- Full trace/config/frame/edge/status manifest (2,104 artifacts): [results/artifact_manifest.csv](results/artifact_manifest.csv), SHA-256 `66308402630b8f1d25f6741dc920a301fd9642ea0aa472115a5fc14e5ed4bead`.
- Timeline overlay SHA-256 `5c0771a14a5b42810deb9d904f2eedbde5dcd92c08c600fa831623956854df0e`; package init `8484ab55108d8943ed984a7e258e317243c4f0530a0df627cb6b2150c1a569e6`.
- A2d item1 donor hashes recorded per trace: timeline `c10fa53afaf4ce323835ed0ffd87de0322b6df7ccc63918c22736b409c13a8a4`; frame generator `346ee8bc8399fbe1fa010927082a34c9156f56283512ecafe00d69d573a1b6bf`; dynamic assembler `8e75cb59139516bfcc6ccfe672281575c4e8490fdf03d5d5bbcbef8a8b203c42`.
- A1 graph files and fixed probes are the A2c-frozen N=92 realization-1 graphs; each trace config stores its graph edge-list hash.

**Known limitations (mandatory carry-forward):** (1) life and mean up-run remain confounded under the A2a stability rule; (2) timeline diversity is family-independent by construction; (3) generator is patched non-upstream; (4) A2b gate is non-binding by construction because of greedy max-min selection; (5) Level 2 route diversity is tie-break-sensitive; (6) time-respecting reachability permits waiting and is not an OLSR/AODV/DSDV oracle. No protocol variants, no ns-3, and no A3.
