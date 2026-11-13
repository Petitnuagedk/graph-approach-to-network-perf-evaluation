# Beta sweep plan

Preparation only; no row in this plan has been executed.

## Exact expansion

The plan is the Cartesian product of the following registered dimensions:

- 5 topology families: geodesic, RGG, WS, ER, BA.
- 3 sizes: N=42, 92, 162.
- 2 protocols: AODV, OLSR.
- 20 dynamic parameter cells per topology-size-protocol stratum: the one-axis union of life levels 0.1–0.9 excluding base life 0.8, stability levels 0.8 and 1.0, and persistency levels 0.1–0.9. Duplicate base coordinates are excluded.
- Phase 1: seed 42, 5×3×2×20 = 600 dynamic variants.
- Phase 2: seeds 43, 44, 45, 46, 5×3×2×20×4 = 2,400 dynamic variants.
- Total registered dynamic variants: 3,000.

`plan_beta.csv` is the execution-stratum index. Each row fixes topology, N, protocol, seed, channel/load window, and the 20-cell parameter expansion. The expansion must be materialized as one run record per parameter cell before any authorized execution; life/stability feasibility comes from `B0/feasibility_F300.csv`, and infeasible cells are `infeasible_not_run`.

## Stop condition

The root Beta charter records a 500-protocol-variant cap. Phase 1 alone is 600, so the registered design exceeds the recorded cap. This conflict is reported, not silently reduced or amended. No Beta execution is authorized until the user explicitly resolves it and A4.5 supplies the required static reference.
