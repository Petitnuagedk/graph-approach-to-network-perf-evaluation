# Beta parameter–flow coupling audit

**Date:** 2026-11-13  
**Scope:** B3 N=42 dynamic protocol block  
**Question:** Are YaDyGaGa path-life, stability, and persistency constraints imposed on the same source–destination pairs that generate the `phi` background traffic?

## Finding

**No. The current B3 implementation does not entangle the generator constraints with every `phi`-generated traffic pair.**

The constraints are pair-specific at generation time, but the selected pair is the frozen A1 probe pair for each family. The ns-3 run then creates the probe flow plus the `phi`-selected background flows. Those background pairs are not passed back into YaDyGaGa and are not used to define the requested path life, stability, or persistency.

Therefore:

- The requested life/stability schedule is directly constrained for the A1 probe pair used to build the frame pools.
- The background pairs generated from `phi` experience the resulting graph-wide frame sequence, but their own path availability, up-run count, stability, and path-ID persistence are not constrained to the registered values.
- The registered parameter value should consequently be interpreted as a **probe-pair-conditioned generator parameter**, not as a pairwise guarantee for the complete offered traffic set.

This distinction is material because the B3 response metrics summarize the probe and background flows together while the dynamic generator's exact constraint is established only for one pair.

## Evidence

### 1. Generator pair selection

The B3 runner reads `probe_S` and `probe_R` from the A1 graph covariates and calls `FrameGenerator.generateSPCFrames` with those two endpoints. This occurs in the preflight and execution paths: [run_b3.py](simple-graph-experiments-v2/beta/B3/run_b3.py#L153) and [run_b3.py](simple-graph-experiments-v2/beta/B3/run_b3.py#L207).

The frame generator groups up frames by whether that selected source–destination pair has a path and by the shortest-path identity for that pair. The timeline generator then applies the requested life, stability, and persistency values to the timeline/path IDs, and `SPCDynamicGraph.buildDynaGraph` assembles frames from those probe-conditioned pools: [run_b3.py](simple-graph-experiments-v2/beta/B3/run_b3.py#L207-L214).

The B3 ledger records the selected pairs indirectly through the graph IDs and A1 covariates; it does not record per-background-pair dynamic feasibility or stability.

### 2. `phi` traffic construction

The ns-3 command receives the A1 probe pair explicitly through `--flows=Node_S:Node_R`, and separately receives `--flowFraction=0.05` and a flow seed: [run_b3.py](simple-graph-experiments-v2/beta/B3/run_b3.py#L243-L247).

The completed validation output demonstrates the separation. Its `flows.csv` contains 44 flows: one probe flow (`Node_0` → `Node_16`) and 43 non-probe flows. The probe pair is [flows.csv](simple-graph-experiments-v2/beta/B3/runs/b3_geodesic_N42_aodv_s42_life_0.1/flows.csv#L2), while the background pairs begin at [flows.csv](simple-graph-experiments-v2/beta/B3/runs/b3_geodesic_N42_aodv_s42_life_0.1/flows.csv#L3) and continue through the file. The background examples include `Node_38` → `Node_13`, `Node_7` → `Node_13`, and many other pairs that are not the generator's selected probe pair.

The output therefore confirms that the parameter-constrained pair and the `phi` background-pair population are not the same set.

### 3. What is shared

All flows do use the same emitted 420-frame matrix in the ns-3 invocation: 120 warm-up frames followed by the 300-frame dynamic sequence. Thus the parameters can affect background traffic indirectly through graph-wide connectivity, route discovery, contention, and failures. This is a real shared environmental effect, but it is not equivalent to enforcing the requested stability or persistency for each background pair.

## Stability-specific answer

For a registered stability value, the value controls the number and arrangement of up-runs in the timeline generated for the probe pair's path-conditioned frame pool. It is **not** measured or enforced as the stability of each pair selected by `phi`.

For example, in the validation row the ledger specifies life `0.1`, stability `0.9`, persistency `1.0`, and probe pair `Node_0` → `Node_16`: [plan_b3.csv](simple-graph-experiments-v2/beta/B3/plan_b3.csv#L2). The dynamic generator was conditioned on that probe pair. The 43 background pairs in [flows.csv](simple-graph-experiments-v2/beta/B3/runs/b3_geodesic_N42_aodv_s42_life_0.1/flows.csv#L3) were not individually checked against stability `0.9`.

## Consequence for the scientific claim

The current data can support a narrower statement:

> Under a frame sequence constructed by imposing the registered YaDyGaGa parameters on the A1 probe pair, routing performance was observed for a `phi`-generated set of background pairs sharing that sequence.

The current data cannot support the stronger statement:

> Every `phi` traffic pair was generated with, or individually experienced, the registered path-life, stability, or persistency value.

The stronger statement would require an explicit pair-aware design in which the traffic-pair set is fixed before generation, every pair is included in the generator's feasibility and metric checks, and the per-pair realized life/stability/persistency is recorded before protocol execution.

## Decision status

This audit is a **design finding**, not a code change. No code was modified for this report. B3 results must not be described as pairwise `phi`-entangled stability/persistency experiments unless the design is separately amended and validated. No claim is made here about the uncompleted rows; the evidence is based on the registered runner and the completed one-row validation.
