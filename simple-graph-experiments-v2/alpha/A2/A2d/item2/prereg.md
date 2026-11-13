# A2d item 2 preregistration — MPC scale and source-overlap probe

Registered 2026-10-09 after A2d item 1 result was entered in `alpha/gates.md`, before item 2 source copy or generation. Generator-only; 0 protocol variants, no ns-3. Isolated copy of exact A0-R2 tree only, unmodified; explicit `behavior="legacy"` baseline path. No protected/source checkout edits. Do not start item 3 until this item’s result is logged.

## Fixed probe design

Use A1 N=92 ER realization 1 only (`er_N92_r1`, edge list/hash and A1 probe are fixed in the A2/A2c prereg). For each of two arrangements make nested pair sets of size 2, 4, and 8:

- **Disjoint endpoints:** for j=0..7, pair `(2j, 2j+1)`, giving `[(0,1),(2,3),...,(14,15)]`.
- **Shared source:** for j=0..7, pair `(5, 6+j)`, giving `[(5,6),...,(5,13)]`.

These endpoints are fixed before output inspection; all are present in the connected static graph. Run 3 independent seeds `{11,29,47}` per arrangement×pair-count, total 18 operations. Per operation, generate a single 3,000-frame MPC pool with `p_edge=.5` and pool seed `seed+10000`; generate one 120-frame synchronous MPC timeline for `path_life=.5`, stability=.5, persistence=.75 and timeline seed `seed`; assemble once with seed `seed+20000`, `no_double=True`, `allow_hamming_fallback=True`, `force=True`. These settings deliberately expose the generator’s registered fallback behavior; do not constrain or silently substitute the assembler.

Each operation is a child process with 60-second wall timeout; timeout or exception is a failed observation, no retry and no replacement. Write operation `config.json` first with graph/pair lists and hash, operation seeds/args, generator/source hashes, Python/NetworkX versions, timeout, and prereg hash. Persist complete requested timeline, MPC pool statuses/counts, selected frame indices/statuses, assembled frames/edges and per-pair per-frame routes/connectivity. Record total generation time, pool-generation time, timeline time, assembly time, and output serialization separately.

## Measures and fixed thresholds

For each pair report requested up-frame fraction from the MPC timeline, measured connected-frame fraction from assembled graphs, absolute error, requested/realized per-pair up-run counts, and all per-frame statuses. Also report the requested joint status-tuple distribution versus realized joint tuple distribution (all $2^m$ tuples), selected-frame reuse count, number of requested route IDs that were changed/fallback, missing requested statuses, and whether the static graph is unchanged. Report seed-level metrics and cell mean/SD (`ddof=1`) when n>1.

Registered numeric criteria: (1) every operation must complete within 60 seconds; (2) every per-pair measured uptime absolute error <=.05; (3) all pair endpoints remain the preregistered ones; (4) no sampled frame edge lies outside the hashed ER skeleton. Do not require exact path-ID realization or joint status distribution, but quantify them to locate limits. No post-result performance cutoff, pooling across arrangements, or inferential claim. Status counts and path-ID-preservation rates are descriptive, not hidden pass criteria. Report the largest tested m=8 as the empirically observed limit **only if** all three m=8 operations in an arrangement pass both runtime and per-pair fidelity; otherwise report the observed limit as below 8 for that arrangement and identify exact failures. A pass means tested configurations only, not general capacity or ceiling.

## Compatibility and accounting

The legacy frame sampler, timeline sampler, and assembler are used without modification from isolated A0-R2 tree `32b243bc84b587f1782ead0d0ac56382a57425e5`; record all source hashes. This item does not invoke patched-v3 from item 1. No ns-3, no A3/Beta, no source changes, 0 protocol variants. Keep disjoint and shared-source results in separate rows/tables.
