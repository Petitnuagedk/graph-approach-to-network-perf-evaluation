# B0 adapted preregistration — F=300 feasibility and provenance

**Registered:** 2026-11-12. **Execution:** read-only preparation; no Beta protocol run.

G0 and G1 are retained as PASS from the existing B0 record. The A4.4 correction is retained: A4.4 was dynamic frame replay with unknown producer and parameters.

G2 is PASS for the Beta generator copy only if all pinned source hashes match the exported copy and the selector is `patched`: timelineBlockGenerator `c10fa53afaf4ce323835ed0ffd87de0322b6df7ccc63918c22736b409c13a8a4`, frameGenerator `e84971f89cb966a574bf447ce8135c0c241b407be14e5066db2f82f3c2ec6b4b`, dynaGraph `8e75cb59139516bfcc6ccfe672281575c4e8490fdf03d5d5bbcbef8a8b203c42`, and toolbox `a5b977aaff8aa132d3b7c53b6609863fb6393e94a03bee239a12399ce144e485`. The exported copy and tree are recorded in `source_provenance.json`; selector `behavior="patched"` is required on every call.

G3 is not applicable to the historical A4.4 replay. Beta path-life, stability, persistency, seed, selector, trace hash, and configuration are recorded per run.

At F=300, for every 0.1-step life/stability pair, compute U=round(300*life), D=300-U, K=round(1+(1-stability)*(U-1)), clamp K only to [1,U], and mark feasible iff K<=D+1. Life 1.0 is a static reference and is not generated. Persistency does not enter feasibility. The infeasible smoke cell must raise ValueError; no substitution is permitted.

B1 is blocked until A4.5 has a completed seed-42 AODV and OLSR static reference record. No B1 run is authorized in this preparation stage.
