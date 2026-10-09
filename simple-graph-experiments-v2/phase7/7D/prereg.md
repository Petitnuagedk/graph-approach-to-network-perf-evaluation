# Phase 7D preregistration — versioned S–R timeline redesign

**Registered before implementation and trace generation: 2026-10-08.** This is a generator-only workstream. It authorizes code and offline validation only: **0 graph-run invocations and 0 protocol variants**. Do not edit Phase 0–6 experimental inputs/results or the external YaDyGaGa checkout. Implement an isolated, versioned J2 adapter under `phase7/7D/`; preserve the legacy generator path unchanged. The boundary decision is free linear endpoints: either endpoint may be up or down; the trace is not cyclic and has no last-to-first transition.

## Design contract

- Use 60 frames at 1 fps for validation. Compute exact up quota as $U=\lfloor60p+0.5\rfloor$, down quota $D=60-U$ (half-up rounding, not language-default banker’s rounding).
- For interior quotas, target mean up-run length 5 frames and use a feasibility-capped run count $K=\min(\lceil U/5\rceil,D+1)$. For $U=0$, use $K=0$; for $U=60$, use $K=1$. This explicit cap is required by the free-endpoint linear constraint that $K\le D+1$; report the realized mean $U/K$. Do not claim a 5-frame mean when the quota makes it infeasible.
- `stability` controls only CV of the positive up-run lengths, conditional on fixed $U$ and $K$: 1 targets the minimum attainable CV among positive-integer compositions; 0 targets the maximum. Use an independent deterministic timeline RNG to choose among tied/near-target compositions and positions. The chosen endpoint-state pattern is selected once per parameter cell and held constant across its five realization IDs and stability values, so the transition count is fixed when comparing realizations/stability; endpoints are not required to be down.
- Place runs without overlap, preserving exact U and D. Persistency affects only path-identity selection among connected graph-pool members; it must not affect the Boolean schedule, its hash, quota, run lengths, or transitions.
- Derive independent reproducible streams from SHA-256 domain-separated keys; do not use global `random.seed()` or Python `hash()`. The `timeline` key includes generator version, master seed, topology, frame count, path life, stability, realization ID, and stream tag, but deliberately excludes `pathPersistency` so a persistency-only change cannot alter the S–R bit string. The `graph_pool` key includes version/master/topology/realization/tag. The `path_identity` key includes version/master/topology/parameter tuple/realization/tag. Record every derived key/seed.
- Assemble matrices from topology-specific Phase 5 up/down pools, determined by S–R connectivity using the serialized node-label order. The stream selecting pool members is independent of the stream generating Boolean schedules. Record input hashes, generator version, seed-key fields, bit-string hash, U/D/K, measured run lengths/CV, and output hash.

## Offline acceptance criteria (fixed before generation)

The validation set is every unique Phase 5 tuple identified by `7A/integrity_audit.md` for each of line, two-lines, and ladder (39 topology × parameter-tuple cells total), with five realization IDs per cell. Do not count repeated center materializations as extra cells.

For every cell:

1. Every one of its five generated traces must have exactly $U$ S–R-up frames; quota error must be 0 frames.
2. For nondegenerate quotas ($0<U<60$), all five S–R bit strings must be distinct, and their mean pairwise Hamming distance divided by 60 must be at least 0.10 (at least 6 differing frame positions on average over 10 pairs). If infeasible or failed, report the cell; do not lower thresholds.
3. For degenerate $U\in\{0,60\}$, diversity is mathematically impossible; require the single exact all-down/all-up timeline, report it as `degenerate/not diversity-eligible`, and do not count it as an acceptance pass for item 2.
4. Same complete seed key must regenerate byte-identical frames and metadata. Changing only realization ID must change every nondegenerate timeline.
5. Changing only `pathPersistency` must preserve timeline hash, exact quota, run lengths, and transition count for all compared settings.

Stability semantics receive a separate fixed-parameter check at path life 0.5 over stability 0.0, 0.2, 0.4, 0.6, 0.8 and five matched realization IDs: U, K, realized mean up-run, endpoint pattern, and transition count must remain identical across the stability settings for each realization. Mean measured CV across the five IDs must be nonincreasing as stability rises, allowing at most 0.05 adjacent reversal; the mean CV at 0.0 must exceed that at 0.8 by at least 0.10. If these thresholds fail, the redesign fails offline acceptance; no simulator runs follow.

Report per-cell unique timeline count, normalized mean pairwise Hamming distance, requested path life, measured uptime, quota error, run count, measured mean run, CV, and deterministic-repeat result. These offline checks cost 0 protocol variants. A passing generator audit does not authorize 7C or a campaign.

## Additional read-only checks before B1

- **6A H4 ±1 s sensitivity:** reuse the 15 stored 6A static packet-event records and their corresponding oracle usable-up intervals. Recompute loss attribution with the correctly shifted interval origin at +44 s, +45 s (reference), and +46 s. For each offset, report pooled static losses, losses sent inside usable intervals, the fraction of those inside their first usable second, and corresponding percentages. Do not change packet timestamps, run simulations, or change H4's classification threshold after results. This is sensitivity analysis, not a correction to source data.
- **6B ladder control provenance:** inspect the Phase 1 static ladder input and saved 6B ladder run config/result; count blank-delimited source matrices, distinct matrices, source SHA-256, fps, requested/effective warm-up, applied frames and trace-time span. Recover authorship from a saved generator/source or session record if possible; otherwise label authorship unknown. No rerun and no Phase 0–6 input/output edits.

## Follow-on run gates (preregistered before implementation)

### B1 static/oracle check

Before the first B1 invocation, the no-interpolation profile must be implemented as opt-in v2 while absent-profile/explicit-legacy settings remain unchanged. B1 uses the planned three 60-frame alternating single-hop runs (down-loss 125, 200, 1,000,000 dB; static only) and two all-up controls (line and ladder), for at most **5 protocol variants**. The static-versus-Python-oracle acceptance tolerance is fixed at **absolute PDR minus no-interpolation usable-uptime error ≤0.05 in every one of the three alternating runs**. Also require zero deliveries in down frames, exact Python/C++ frame/usable uptime, and identical all-up-frame delivery counts across down-loss variants. For the all-up controls, use 60 source frames at 1 fps and zero warm-up; require at least 300 offered packets, at least 297 delivered, and PDR ≥0.99. A static/oracle miss fails B1 and means static cannot serve as the dynamic effective-uptime reference without a different design. No tolerance changes after seeing results.

### B2 legacy regression

After B1 passes, run exactly the existing B0 trace/config/seed/routing under explicit legacy settings, costing 3 variants. Compare deterministic outputs against B0: packet event CSVs and route logs byte-for-byte; compare results after removing only the explicitly nondeterministic wall/CPU-time columns; all packet counts, delivery/loss fields, route/channel-state fields and resolved legacy settings must match exactly. Any mismatch fails B2 and blocks 7C. No output normalization beyond the stated timing columns is allowed.

### Pilot sizing gate

After B1/B2 and generator acceptance, run one preregistered target-length trace/replay measurement before sizing the pilot. Budget unit is graph-run invocations × protocol variants; a single static-only invocation costs one variant, regardless of the number of trace frames or packets. Record build/startup and simulation wall time separately. Use measured cost, not historical estimates, for a pilot proposal. The pilot question is the path-life effect across validated diverse timelines; do not repeat Phase 5. This preregistration authorizes no pilot until a separate capped pilot plan is approved.