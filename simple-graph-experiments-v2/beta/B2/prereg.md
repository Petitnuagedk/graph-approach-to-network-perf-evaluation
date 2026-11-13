# B2 preregistration — N=42 axis characterization

**Authorized:** 2026-11-13. **Status:** execution authorized; generator-only; no ns-3 protocol variants.

B2 characterizes the registered YaDyGaGa A0-R2 patched build (`5a497f51815c85552fb0998b723460f16d0f50a0`, `behavior="patched"`) on the five N=42 A1 realization-1 skeletons: geodesic, RGG, WS, ER, and BA. The A4.5 static reference is not regenerated.

## Frozen frame-pool grid

Use the existing A2 grid: `p_edge` in `{0.3, 0.5, 0.7}`, frame-pool trials in `{3000, 10000}`, pool seeds `{11, 29, 47}`. Each pool uses the pinned legacy `FrameGenerator.generateSPCFrames` draw process. The B2 timeline seed is 42.

## Axis cells

For each pool, characterize the registered one-axis cells:

- path life: `0.1`–`0.9`, excluding `0.8`, with stability `0.9`, persistency `1.0`;
- stability: `0.8` and `1.0`, with path life `0.8`, persistency `1.0`;
- persistency: `0.1`–`0.9`, with path life `0.8`, stability `0.9`.

The timeline length is F=300. The exact feasibility rule is `K <= D+1`; infeasible cells are recorded as `infeasible_not_run`. Life `1.0` is the A4.5 static reference and is not generated dynamically.

## Measurements

Record requested and realized life, up-run count, down-run count, transitions, path-ID retention, assembled shortest-path identity retention where defined, alternative-path presence, pool counts, replacement feasibility, and frame-pool provenance. Persistency is considered structurally inert on a skeleton if changing its value does not change the assembled route-level metrics under the fixed timeline/pool/seed conditions. This is a descriptive generator/oracle result, not a protocol-routing result.

No retries, substitutions, clamping, or ns-3 execution. B3 remains gated after this characterization.
