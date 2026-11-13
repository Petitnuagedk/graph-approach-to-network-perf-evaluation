# A2f-1 preregistration — exact-quota timeline boundary and timer ratios

Registered before calculation or table generation. Scope is offline integer/formula work only: no timeline sampling, frames, source changes, simulations, ns-3, or protocol variants. All new artifacts remain under `alpha/A2f/A2f-1/`.

## Frozen calculation

Grid: `F ∈ {60,120,240}`, `life ∈ {0.1,0.2,...,0.9}`. For every cell use Python round-to-even `U=round(F*life)`, `D=F-U`, `K_max=min(U,D+1)`. For nontrivial cells exactly feasible up-run counts are integer `K=1..K_max`, and exactly feasible mean-up lengths in frames are the discrete set `{U/K : K=1..K_max}`. No real-valued interpolation is counted as exactly feasible. For each K use `J_min=max(1,K-1)` and `J_max=min(D,K+1)`; feasible mean down-run values are `D/J` for all integer J in this inclusive range. Report at both K extremes and overall extrema across feasible K. Trivial U=0 or D=0 cells are outside this grid.

Time conversion: `mean_up_seconds=(U/K)/fps`; `rho=mean_up_seconds/timer_seconds`. Report min/max rho over all feasible K for each cell and the requested fps/timer axes. Timer mapping is fixed as OLSR Hello=2 s, OLSR TC=5 s, AODV Hello=1 s, AODV ActiveRouteTimeout=3 s; fps `{0.5,1,2,4}`. These are dimensional ratios only, not protocol-performance thresholds.

## Numeric gates and hand checks

1. Exactly 27 life/frame rows and exactly 432 life/frame/fps/timer rows are emitted; all `U,D,K_max,J` values are integers and every formula identity holds (100%).
2. Exactly-feasible mean-up support is represented as the full finite set `{U/K}`; no off-lattice mean is called exactly feasible. Explicitly identify out-of-range and in-range-but-off-lattice values as unreachable for an exact-quota binary timeline.
3. Hand-check these three preregistered cells: (a) F=60, life=.5: U=30,D=30,Kmax=30, mean-up range 1..30 frames; (b) F=120, life=.9: U=108,D=12,Kmax=13, mean-up range 108/13..108 frames; (c) F=240, life=.1: U=24,D=216,Kmax=24, mean-up range 1..24 frames. Down-run range is independently verified from the registered J formula.
4. Save CSV tables, calculation script, exact command, and SHA-256; append the gate and hashes to `alpha/gates.md` before registering or executing A2f-2.

There are no statistical tests or stochastic execution in this sub-stage. Limitations to carry forward: life and mean up-run are confounded under the A2a stability rule; timeline diversity is family-independent by construction; generator is a patched non-upstream copy; the A2b gate is non-binding by construction (greedy max-min selection); Level 2 route diversity is tie-break-sensitive; time-respecting reachability permits waiting and is not an OLSR/AODV/DSDV oracle. No EM work. Budget 0 protocol variants, no ns-3, no A3.
