# Beta status update

**Status update (recorded 2026-10-13; amended 2026-11-12): preparation only; no Beta run is authorized or launched.**

| Record/section | Status | Open | Superseded by A4.5 correction |
|---|---|---|---|
| Charter and research question | retained | dynamic effects remain descriptive; no ranking or ceiling language | A4.4 baseline wording |
| Baseline definition | superseded | wait for the completed A4.5 static reference | A4.4-derived baseline and outcomes |
| Dynamic axes | retained/adapted | path life, stability, persistency on the registered F=300 grid | none |
| B0 | adapted read-only | G2/G3 re-score is recorded below | A4.4-based G2/G3 failure interpretation |
| B1 | blocked | requires exact A4.5 seed-42 AODV/OLSR records | A4.4 harness comparison |
| B2–B5 | not started | require B1 and later user authorization | prior A4.4-dependent plans |
| Budget | registered plan | Phase 1 is 600 dynamic variants; Phase 2 is 2,400; total 3,000, checked against the Beta cap | Alpha ledger discrepancy is not resolved here |

**Cap conflict:** the existing root Beta charter records a 500-protocol-variant cap. The registered Phase 1 count of 600 already exceeds that cap. The 3,000-variant design is preserved without reduction or silent cap amendment; execution stops for an explicit user decision.

## Revised registered design

The sweep uses F=300 frames and sim time 300 s. Path life, stability, and persistency levels are 0.1–1.0 in steps of 0.1. Path life 1.0 is the A4.5 static reference and is not generated or swept. The base point is life 0.8, stability 0.9, persistency 1.0. Each axis is swept one at a time: life 0.1–0.9 excluding 0.8; stability 0.8 and 1.0; persistency 0.1–0.9. Infeasible life/stability pairs are `infeasible_not_run` and are never substituted or clamped.

Scope is five topologies, N=42/92/162, AODV/OLSR, phi 5%/1.5%/0.65%, warm-up 120/180/320 s, and window [warm-up,warm-up+300]. Phase 1 uses seed 42 only. Phase 2 uses seeds 43–46 only after review and approval. YaDyGaGa is pinned to commit `5a497f51815c85552fb0998b723460f16d0f50a0`, tree `32b243bc84b587f1782ead0d0ac56382a57425e5`, with `behavior="patched"` explicitly selected.

No Beta run is launched by this status record.
