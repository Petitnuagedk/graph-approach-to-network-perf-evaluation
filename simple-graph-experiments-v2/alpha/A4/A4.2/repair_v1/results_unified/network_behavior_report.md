# A4.2 network behavior and simulation setup

## Scope

A4.2 is a fixed-window load sweep over five graph architectures, three graph sizes, two routing protocols, and three offered-load levels:

- Architectures: Barabasi-Albert (BA), Erdos-Renyi (ER), geodesic, random geometric (RGG), and Watts-Strogatz (WS).
- Sizes: N = 42, 92, and 162 nodes.
- Protocols: AODV and OLSR.
- Background loads: phi1, phi5, and phi10, corresponding to 1%, 5%, and 10% of unordered node pairs.
- Coverage: 5 x 3 x 2 x 3 = 90 successful runs.

Each architecture-size combination is one stored graph realization. Consequently, the results compare the selected realizations and are not a multi-realization estimate of family-level variation.

## Simulation setup

Each run uses a 240-frame fixed window at 1 frame/s:

- 120-frame warm-up.
- 120-frame measurement window.
- Simulation stop at approximately t = 239 s.
- One probe flow plus the selected background flows.
- Data rate: 50 kbps.
- Packet size: 1024 bytes.
- Transmit power: 20 dBm.
- Link-up loss threshold: 10 dB.
- Link-down loss threshold: 125 dB.
- Interpolation enabled.
- Routing instrumentation and route dumping enabled.
- Random seed: 42; flow and routing seeds are recorded per run.

The unified data and run artifacts are stored in [results_unified](.). The run table is [per_run.csv](per_run.csv), and the graph covariates are [graph_characteristics.csv](graph_characteristic_plots/graph_characteristics.csv).

## Static graph structure

The first adjacency matrix in each frame-stacked input was used for the static graph descriptors. All 15 inputs were symmetric and connected.

The architectures have similar mean degree, approximately 5.2--6.4, but substantially different global structure:

- Geodesic graphs have low degree inequality, high clustering, and the largest diameter as N increases.
- WS graphs have degree close to 6, low degree inequality, high clustering, and also large diameter, reaching 17 at N=162.
- BA graphs have the strongest degree inequality and the highest degree centralization among the families. Their diameter remains comparatively small.
- ER graphs have low-to-moderate clustering and low centralization, with diameter increasing from 5 to 6.
- RGG graphs have high clustering and comparatively large diameter, reaching 13 at N=162.

The architecture figures are available in [architecture_plots](architecture_plots), including a 3-D topology view of the N=162 geodesic graph. The 3-D view is a force-directed embedding normalized onto a sphere; it is not a reconstruction of physical coordinates.

## Observed network behavior

### Small graphs: N=42

The network is generally able to deliver the post-readiness traffic across all loads. Mean post-readiness background PDR is 1.0 for both protocols and all three loads. However, the full-window PDR falls at phi10, to approximately 0.879 for AODV and 0.827 for OLSR, because convergence and readiness consume part of the fixed window.

AODV control traffic increases strongly with load, from about 273 mean control packets at phi1 to about 1,578 at phi10. OLSR remains comparatively stable, from about 213 to 224 mean control packets. Probe delay remains low, approximately 1--2 ms.

### Medium graphs: N=92

At phi1, post-readiness PDR remains high: approximately 0.999 for AODV and 0.997 for OLSR. At phi5 and phi10, most runs have no non-empty post-readiness measurement window, so post-readiness PDR is undefined. These cells are not equivalent to zero PDR.

The full-window values nevertheless show severe degradation at higher load. AODV background median PDR decreases from approximately 0.992 at phi1 to 0.040 at phi5 and 0.004 at phi10. OLSR decreases from approximately 0.868 at phi1 to 0.381 at phi5 and 0.046 at phi10.

AODV control traffic rises from about 420 mean packets at phi1 to more than 15,900 at phi5 and phi10. OLSR control traffic remains near 260--280 packets. Probe delay becomes much more variable, reaching approximately 1.1 s for AODV at the two higher loads.

### Large graphs: N=162

At phi1, post-readiness PDR is high where readiness is reached: approximately 1.000 for AODV and 0.988 for OLSR. The full-window PDR is much lower, approximately 0.595 for AODV and 0.586 for OLSR, reflecting long convergence relative to the 120-frame measurement design.

At phi5 and phi10, the AODV and OLSR runs do not provide non-empty post-readiness windows. Full-window background PDR is approximately zero for AODV and decreases from 0.021 to 0.006 for OLSR. These values indicate that the fixed window is dominated by convergence and/or severe load-related degradation; they should not be presented as clean post-convergence load measurements.

AODV control traffic is high at N=162, increasing from approximately 6,329 mean packets at phi1 to 16,589 at phi5 and 18,079 at phi10. OLSR control traffic is much lower and slightly decreases with load, from approximately 364 to 299 mean packets. This contrast is descriptive for the tested realizations and does not constitute a protocol ranking.

## Relationship to graph characteristics

The characteristic-performance plots compare PDR, delay, and control traffic with diameter, mean shortest-path length, clustering, degree centralization, and node connectivity. The clearest structural pattern is size-related: larger graphs have longer paths and larger diameters, and they reach readiness less reliably within the fixed 120-frame warm-up/measurement design.

The topology metrics also separate the architectures: geodesic and WS graphs retain high clustering but have long paths, while BA graphs have stronger degree concentration and shorter paths. RGG graphs combine high clustering with large diameter. These structural differences are consistent with different convergence and control-traffic behavior, but the present design has only one realization per family-size cell and all runs carry readiness flags. Therefore, the plots support hypotheses about topology-performance relationships, not causal or family-wide conclusions.

## Interpretation limits

- Readiness was flagged in all 90 runs.
- Missing post-readiness values mean that no valid post-readiness window existed; they are not zeroes.
- Open markers in the plots indicate full-window fallback values where post-readiness values are unavailable.
- The first 60 rows and last 30 rows are unified in one table, but rows 61--90 were run in the unrestricted continuation and have synthetic resource-guard metadata.
- The analysis uses one realization per architecture and size; replication is required before generalizing across graph families.
- No protocol ranking, load ceiling, or causal claim is made here.
