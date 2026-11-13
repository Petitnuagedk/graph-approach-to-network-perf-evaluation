# Beta design note — written after A4.4 results

This is a design note only; no Beta run is authorized.

## Dynamic axes

Beta should vary one axis at a time: path life, stability, persistency, random-link fraction, random-link lifetime, and number of constrained paths. The A0-R2 and A2 evidence supports path life and seed diversity on the patched copy; stability and persistency are partly usable; random-link fraction and random-link lifetime are not usable under YaDyGaGa because its unconstrained edges are redrawn i.i.d. per frame rather than controlled as a lifetime process. The number of constrained paths is not established as a general capability and requires explicit validation.

## Proposed baseline-anchored grid

Use the A4.4 baseline's five families, N={42,92,162}, protocol={AODV, OLSR}, phi={5%,1.5%,0.65%}, warm-up={120,180,320 s}, 300 s post-warm-up, and window `[warm-up,warm-up+300]`. Vary one dynamic axis at a time while holding all other baseline settings fixed. A future prereg must set Beta's numeric cap in protocol-variant units and provide an axis-specific budget line.

For random links, the design decision is unresolved. Before any Beta preregistration, the user must choose between an explicit Edge-Markovian fallback or a YaDyGaGa extension. The Edge-Markovian option requires a separate design note and user approval; it would need explicit stationary up-fraction and mean-up-lifetime parameters and would not claim YaDyGaGa provenance.

Beta's counting unit is protocol variants, not packets, frames, or elapsed time. No numeric Beta cap is set here.
