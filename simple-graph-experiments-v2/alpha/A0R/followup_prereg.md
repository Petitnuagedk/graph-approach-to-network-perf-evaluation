2. **Life-diversity sweep:** life ∈{.1,.3,.5,.7,.9}, stability=1.0, persistency=.9, frames=120, N=92, seeds 42–91 (50 per life). The common stability=1.0 keeps every quota/run combination feasible, including life=.9, and is held constant across the sweep. Use 500 candidate frames, p_edge=.5, frame seed `seed+10000`, assembly seed `seed+20000`. Report unique assembled S–R strings and mean pairwise normalized Hamming fraction at each life. For life=.5 this is the requested 50-seed check; other lives use the same 50 seeds for comparability.
# A0-R offline follow-up preregistration

Registered 2026-10-09, before follow-up measurements. All measurements use the existing isolated patched copy; no ns-3, network protocols, or protocol variants. Do not change the frozen A0 thresholds. Do not run A1 as part of this follow-up.

## Required checks

1. **Stability × persistency on assembled patched traces:** N=92 geodesic, diameter S–R pair, 120 frames, path_life=0.5; stability ∈{0,.2,.4,.6,.8,1.0}, persistency ∈{0,.25,.5,.75,1.0}, seeds 42–51 (10 each). For each condition use an independent candidate-pool seed `seed+10000` (500 p_edge=.5 frames) and assembly seed `seed+20000`. Report input Boolean timeline transitions and mean contiguous up-run length, assembled S–R transitions and mean contiguous S–R up-run length, and path-ID changes/within-run identity retention. The Boolean schedule should be invariant to persistency at fixed stability/seed; report rather than assume.
2. **Life-diversity sweep:** life ∈{.1,.3,.5,.7,.9}, stability=.8, persistency=.9, frames=120, N=92, seeds 42–91 (50 per life). Use 500 candidate frames, p_edge=.5, frame seed `seed+10000`, assembly seed `seed+20000`. Report unique assembled S–R strings and mean pairwise normalized Hamming fraction at each life. For life=.5 this is the requested 50-seed check; other lives use the same 50 seeds for comparability.
3. **N=162 candidate-pool sizes:** frequency-4 geodesic graph, lexicographically first diameter pair, 500 candidate frames, p_edge=.5, seeds 42–91. Report each seed's up frames, route groups, down frames, empty/tiny status, and elapsed time; tiny remains the previously declared descriptive `<5` frames, not an acceptance threshold.
4. **Dirty-source diff:** preserve the exact diff of the A0-R patch's `timelineBlockGenerator.py` against the current dirty YaDyGaGa `timelineBlockGenerator.py`, plus the dirty file's SHA-256 and comparison to the pinned clean commit. Do not edit or import the dirty checkout.

## Classification/authorization boundary

Do not alter A0's historical verdict. If the follow-up checks hold, record the requested qualified A0-R/A0 capability classification, and report the user's conditional A1 authorization. Do not start protocol or A1 work in this offline follow-up; require a separate A1 scope/variant budget and execution request. If a measurement fails or is inconclusive, state that explicitly and keep A1 blocked. No thresholds may be relaxed.
