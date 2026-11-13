# B3 preregistration — N=42 one-axis sweep

**Authorized:** 2026-11-13. **Status:** scope amended and authorized; execution implementation and preflight pending.

B3 is the first protocol-bearing Beta sweep after B1 and B2. It uses the pinned YaDyGaGa A0-R2 patched build (`5a497f51815c85552fb0998b723460f16d0f50a0`, tree `32b243bc84b587f1782ead0d0ac56382a57425e5`, `behavior="patched"`) and the A4.5 static reference.

## Registered block

N=42, all five A1 realization-1 families, AODV and OLSR, F=300, A4.5 channel and traffic settings, interpolation OFF, and seeds 42–46.

The confirmed one-axis block uses ten levels for each dynamic axis:

- path life: `0.1, 0.2, ..., 0.9, 1.0`;
- stability: `0.1, 0.2, ..., 0.9, 1.0`;
- persistency: `0.1, 0.2, ..., 0.9, 1.0`.

Life `1.0` is the A4.5 static reference and is recorded as a reference row rather than generated dynamically. The resulting N=42 block contains 310 absolute protocol-variant rows:

- 300 dynamic one-axis variants: three axes × ten levels × two protocols × five seeds.
- 10 static-reference baseline variants: AODV and OLSR; five seeds.

The dynamic levels are the registered B0/Beta levels: life below/above the base coordinate, stability below/above the base coordinate, and persistency below/above the base coordinate. B2 confirmed the N=42 generator controls and did not classify persistency as inert, so persistency remains in this block. Exact levels and each materialized row must be recorded before execution.

## Frame-pool decision — 2026-11-13

The user selected option (1) for the B3 frame pool. Every dynamic B3 row uses the single registered A2 pool configuration `p_edge=0.5`, `trials=10000`, `pool_seed=11`, with timeline seed equal to the row seed. The other A2 pool configurations are not part of B3 and must not be substituted.

## Arithmetic hold — 2026-11-13

The earlier 310-row statement is not execution-ready. It omits the five-family multiplier and counts the static life-1.0 reference both as a dynamic life level and as additional baseline rows. Under the literal five-family, two-protocol, five-seed scope, the one-axis union contains 29 dynamic levels per family/protocol/seed (life 0.1–0.9, stability 0.1–1.0, persistency 0.1–1.0) plus one shared A4.5 static reference: `5 × 2 × 5 × 30 = 1,500` absolute rows, before feasibility filtering. This exceeds the 1,200 cap. No ledger or simulator run may be started until the user resolves this count/cap conflict; infeasible rows remain charged in the absolute count.

## Execution rules

Use the A0-R2 patched generator only; no substitutions, clamping, retries, or automatic reruns. Check `K <= D+1` before generation and record infeasible cells as `infeasible_not_run`. The static baseline uses the A4.5 all-up matrix and is not generated dynamically. Require at least 8 GiB `MemAvailable` and zero swap. Use at most two workers and user termination; no timeout is imposed.

Stop after the 70-variant N=42 block. Do not start B4. Report per-run PDR, background median and p10, delay, control bytes by type, MAC/collision values, readiness flag, and descriptive attribution. No ranking, ceiling, or causal claims are permitted.

Infeasible life/stability rows remain in the absolute ledger as `infeasible_not_run` and are not silently removed. The amended 1,200 protocol-variant cap covers this 310-row N=42 block. Applying the same ten-level policy to all five families and three sizes would produce 900 Phase 1 rows, not the previously stated 600; the 600 count is superseded by this explicit user amendment. B4/B5 remain separately gated.