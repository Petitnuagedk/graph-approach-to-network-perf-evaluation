# Tango campaign report

## Stop status
Tango remains incomplete. The follow-up guard on 2026-10-22 passed for available memory (24 GiB >= 8 GiB) and passed for swap: no active swap was reported. A draft campaign implementation was added under [tango/src](src/), and the pilot was stopped before T2/T3 completion. The draft T1 output and pilot are historical implementation artifacts; no T1–T4 result is accepted, no figure is accepted, and no gate is evaluable.

## Gate table
| Gate | Observed | Threshold | Status |
|---|---|---|---|
| Environment memory | 24 GiB available | >= 8 GiB | PASS |
| Environment swap | none active | swap == 0 | PASS |
| T1-G1..G4 | draft output only; not accepted | registered thresholds | NOT RUN |
| T2-G1..G3 | not run | registered thresholds | NOT RUN |
| T3-G1..G2 | not run | registered thresholds | NOT RUN |
| T4-G1 | not run | registered threshold | NOT RUN |
| C-G1..C-G2 | not run | registered thresholds | NOT RUN |

## Figure index
P01–P10: not accepted. No figure is judged informative or uninformative; no replacement figure was added.

## Provenance
The required `uk` source was located at `alpha/A2f/A2f-2/source`; its isolated interface was imported by the draft. The A1 manifest and edge-list inputs were read by the draft; no A4 path was touched. Draft source and pilot outputs are not valid Tango results.

## Descriptive observations written after Tango results
The draft produced T1 CSV output before stopping; these are implementation artifacts, not registered Tango results. The child-operation boundary and provenance requirements are documented in [prereg_amendment_1.md](prereg_amendment_1.md).

## Explicit non-claims
This report makes no causal, protocol-ranking, ceiling, timing, reachability-oracle, or realization-independence claim. No geodesic correlation result exists; no seed/frame independence is asserted. Timing was not measured; any future timing field must be labelled `contended`.

## Command
The frozen command sequence is in [run.sh](run.sh). It was not executed because the guard failed.

## Decisions needed from user
The implementation now contains disjoint T3 routeable/non-routeable pools, seeded route assembly with path-persistency handling, realization-level bootstrap calculations, and persisted T1 failure records. The full run generated 60,800 T1 rows, 363 T2 covariate rows, 6,534 T3 trace rows, 837 T4 rows, and 432 correlation rows with no T3 failure rows. The run then stopped in the figure writer because P03 expected `support_M` while the support CSV uses `M`; this was a figure-stage crash, not a simulation-stage crash. P03–P10 have since been regenerated, producing ten PNG/PDF pairs and ten plotted-data CSVs. Scientific acceptance still requires the registered gate and figure-layout review. No Beta work, A4 work, ns-3, or protocol variant is authorized by this stopped campaign.
