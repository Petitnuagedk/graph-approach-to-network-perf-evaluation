# A2f-1 result — exact-quota structural boundary

**Gate: PASS.** The offline calculation emitted 27 `(F,life)` rows and 432 `(F,life,fps,timer)` rows. Formula identities passed for every row; all three preregistered hand checks pass. No traces, source edits, ns-3, or protocol variants were used.

For nontrivial exact-quota traces, the feasible run counts are integers `K=1..min(U,D+1)`. Thus feasible mean-up lengths are the finite set `{U/K}`, not every real value between its extrema. At each K, feasible down-run counts are `J=max(1,K−1)..min(D,K+1)` and mean-down lengths are `{D/J}`. The CSV reports the endpoint ranges at K=1 and K=Kmax and extrema over all K.

| F | Life | U | D | Kmax | Mean-up range (frames) | Overall mean-down range (frames) |
|---:|---:|---:|---:|---:|---:|---:|
| 60 | .1 | 6 | 54 | 6 | 1–6 | 7.7143–54 |
| 60 | .5 | 30 | 30 | 30 | 1–30 | 1–30 |
| 60 | .9 | 54 | 6 | 7 | 7.7143–54 | 1–6 |
| 120 | .1 | 12 | 108 | 12 | 1–12 | 8.3077–108 |
| 120 | .5 | 60 | 60 | 60 | 1–60 | 1–60 |
| 120 | .9 | 108 | 12 | 13 | 8.3077–108 | 1–12 |
| 240 | .1 | 24 | 216 | 24 | 1–24 | 8.64–216 |
| 240 | .5 | 120 | 120 | 120 | 1–120 | 1–120 |
| 240 | .9 | 216 | 24 | 25 | 8.64–216 | 1–24 |

The boundary table carries the full 27-cell grid, each exact discrete `U/K` support, down-run endpoint/interior extrema, and the three explicit hand-checked cells. For example: at `F=120, life=.9`, `U=108,D=12,Kmax=13`, so the shortest possible up-run is `108/13≈8.3077` frames. With K=13 only J=12 is feasible, hence mean down-run is exactly 1 frame. At `F=240, life=.1,K=24`, J=23..25, giving 8.64..9.3913 frames at that K.

## Timer-ratio reachability

For each of the four listed timers and fps `{.5,1,2,4}`, `rho=(U/K)/(fps*timer_seconds)`; the companion table reports both extrema and the entire discrete rho support. Every combination with a mean-up target outside the cell’s extrema is unreachable. Within the extrema, any target not exactly equal to `U/K` (or corresponding rho) is also unreachable: continuous interpolation is not an exact-quota binary schedule. Changing fps rescales seconds/rho but does not alter which frame-domain quotas are combinatorially feasible. Consequently, any desired `(life, mean-up-seconds)` falling below the `Kmax` endpoint or not on the finite exact support is impossible for every exact-quota binary timeline; item 4 cannot fix it. A time-resolution/fps axis is necessary when the desired protocol timer ratio is outside the reported support.

This analysis does not claim Hello/TC/route-timeout semantics from these ratios, nor predict protocol behavior. Ratios are dimensional comparison only.

## Reproduction and hashes

Command: `/home/hledirach/Documents/J2/.venv/bin/python /home/hledirach/Documents/J2/simple-graph-experiments-v2/alpha/A2f/A2f-1/compute_boundary.py` (Python 3.14.4; built-in round-to-even).

- Preregistration SHA-256: `c5ffa38a11d4c0c85601dd9fb1a4db1066866df89e52128fc5ce9fa5264d7b9e`.
- Calculation script SHA-256: `3a6b720ccebe7dd74eacc1df422bebadd9dc295444ad1951afef3dd4cb1d7825`.
- `boundary_table.csv`: `a9317ef2c23a85f3615083114e6a47f1cff0b9cfb80e69412c47c97fe1ae8549`.
- `rho_reachability.csv`: `1c0a5f73f67f2ab65df4f557646d853f7508466e80a86da12ba479e441f964f6`.
- `summary.json`: `79e123a004bd9376acf96fb5eb8d1b061fcc7405a370526283684a79d6b846e2`.

## Limitations to retain in every later table

Life and mean up-run are confounded under the A2a stability rule; timeline diversity is family-independent by construction; the generator is a patched non-upstream copy; the A2b gate is non-binding by construction because selection is greedy max-min; Level 2 route diversity is tie-break-sensitive; time-respecting reachability permits waiting and is not an OLSR/AODV/DSDV oracle. This offline structural boundary does not address those other gates. 0 protocol variants, no ns-3, no A3.
