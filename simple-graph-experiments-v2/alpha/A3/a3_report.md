# Alpha A3 — instrumentation validation report

**Disposition: FAIL. Stop here; do not begin A4.** This report records the preregistered offline checks and eight protocol variants. T1 failed for AODV forwarding accounting; T4 failed the strict frozen Phase 1 compatibility gate. No protocol runs were retried, replaced, or added. The cap is closed at 8/12; the four unspent units are not authorization for more runs.

## Registration and scope

The frozen design is [A3 preregistration](prereg.md), SHA-256 `19d43031809e345ab5f7e6cc1b544420d3de55a8157ac119b0bea905cbdf0398`. The separate budget is [alpha/budget.md](../budget.md), SHA-256 `b34b623866464a0082dd23b86674309407b6165d1d12119207df42d8e9692d1c`. Prerequisite A3-0 was accepted via B1′ and B2; the original B1 failure remains part of the history. Static routing was excluded because 7C is unknown; DSDV was excluded from T1 because of the disclosed Phase 1 instability. No performance ranking, protocol ceiling, or static-route result is claimed.

Only `/home/hledirach/Documents/sp1-sp2/scratch/graph-run.cc` was the registered source target. The unversioned ns-3 3.46.1 tree has no root Git repository. Its pre-edit SHA-256 was `5cd8dfd97aec19b7be5373a6573290cf6c47736e9e516cdf894684e485a7e90f`; final SHA-256 is `0f04a8d87fd261a6544fb76ce5d6e80fa8f4154cdb7aebfd4632b17cd0da4d84`. The final file contains opt-in flow selection/diagnostics, convergence accounting and a self-test entry point. The original pre-edit source snapshot was not retained and the source tree has no Git history; therefore an exact baseline-to-final unified diff cannot be independently reconstructed or claimed. The pre/post identities and this limitation are retained rather than presenting a synthesized diff as exact.

## Registered test outcomes

| Test | Verdict | Evidence |
|---|---|---|
| T1 — forwarding accounting | **FAIL overall** | Both protocols offered and uniquely delivered 391/391 probe packets over the 3-hop path. OLSR forwarded 0/391/391/0 at nodes 0–3, total 782, exactly the expected $391(3-1)=782$; OLSR passes. AODV forwarded 2/391/391/0, total 784; node 0 violates the endpoint-zero check and the total exceeds the expected 782 by two. AODV fails. The two unexpected source-node forwarding callbacks remain unexplained from the saved aggregate evidence; no protocol rerun or post hoc reclassification was made. |
| T2 — flow selection/static distances | **PASS** | Offline flow-selection assertions passed, including exact rounded counts, probe-pair exclusion, uniqueness, deterministic repeated same-seed selection, and observing reverse-direction selection. NetworkX independently checked all 13,041 unique unordered non-self geodesic pairs against the fixed 162-node input; every stored distance matched. `static_hop_distances.csv` serializes one direction per unordered pair, not ordered pairs or self-pairs; distances are symmetric, but this output convention is narrower than a literal ordered all-pairs table. Input hash: `f3735f6b5ac24947a2cb6078d0ea4d6f3c80b012ca3e74e19f0bd32ee779b0bc`. |
| T3 — convergence estimator | **PASS** | Synthetic boundary checks passed: immediate case first delivery 0 s/convergence 10 s; delayed case first delivery 15 s/convergence 24 s; alternating-even deliveries never converge and report NaN. |
| T4 — Phase 1 compatibility | **FAIL overall** | After removing only `wall_time_s` and `cpu_time_s`, flags-off and instrumentation-on/`flowFraction=0` outputs match exactly: all 60 non-timing columns and all three rows. Each current result has 62 total columns; frozen Phase 1 has 18 total columns (60 versus 16 non-timing columns), so both strict Phase 1 comparisons fail. No columns were dropped. For example, Phase 1 OLSR records PDR 1.000 and `app_tx_pkts=296`; both current outputs record PDR 0.822222 and `app_tx_pkts=360`. Reference SHA-256: `58929cd0c14ab0b49bfa41fd977359d1d51314557a37f874ebebe5faab7ccd2c`. |

T2/T3 are offline tests. T1 used the corrected 65-frame all-up fixture at 1 fps; the preregistration addendum records this change from 60 frames. The fixture correction was made before T1 runs. The preregistration ends with a stale sentence stating no T1 variant had yet run; this report clarifies that the two registered T1 variants subsequently ran once each. No other substitution or retry occurred.

## Variant accounting and limitations

Executed/attempted: **8/12** — T1 OLSR/AODV (2); T4 OLSR/AODV/DSDV flags off and the same three with instrumentation and `flowFraction=0` (6). No A4, pilot, extra protocol, seed, or flow-fraction run was started. T4's flags-off/on equality is a positive compatibility subcheck, but it does not pass the separately frozen Phase 1 reference gate. T1's OLSR pass does not rescue the required both-protocol gate. Overall A3 therefore **fails**.

This result is limited to the specified source, build, fixture and replay configuration. It does not establish protocol performance on dynamic or other graph families. Carry forward [Alpha limitations](../LIMITATIONS.md), including the generator/protocol separation, fixed graph/probe coverage limits, and the restriction against causal or ceiling claims.

## Artifact identity

The machine-readable acceptance record is [validation_summary.json](validation_summary.json), SHA-256 `24179fbbeb229159c70b842b70811e55e9c7040e5e8edeee5d31a9c8dc057d12`; its offline analyzer is [validate_a3.py](validate_a3.py), SHA-256 `5302e4cacf176951c9a6b5aaecc71acc847a393c6961d216b6623ab0d02dbb0d`. The complete per-file inventory and SHA-256 values are in [MANIFEST.sha256](MANIFEST.sha256). A single A3 result entry is appended to [the Alpha gates log](../gates.md). This stage ends here, before A4.
