# B2 continuation authorization and comparison freeze

**Written 2026-10-08 before the B2 simulator invocation.** Original B1 failed its aggregate-PDR/oracle criterion; that remains recorded unchanged. B2 is the already preregistered legacy byte-identical regression, which tests preservation of legacy behavior and is independent of how B1/B1′ metrics are interpreted. Under the user's explicit next-step authorization, B2 proceeds as the sole remaining 7B gate despite the prior generic B1 stop wording. This does not authorize the target-length timing probe or 7C.

## Frozen B2 execution

Run the same Phase 5 line trace used by B0 with the exact B0 arguments, changing only `outDir` to a new `7B/legacy_after/` directory. Preserve routing variants OLSR, AODV, and static (one invocation, 3 protocol variants). Require SHA-256 of the input trace to equal B0's `282feae63d0822c096bc427b9e7fc8705447509d352a72a78761805acd81f603`; resolved interpolation true, source 60 frames, 45 inserted warm-up frames, and 105 applied frames for every routing variant. Use the exact command recorded in the B0 config/report, with the new output directory only.

## Frozen deterministic comparison

Compare each protocol's `packets_*.csv`, `routes_*.txt`, `times_*.csv`, `oracle_diagnostics_*.csv`, and `packet_diagnostics_*.csv` byte-for-byte with B0. Compare result CSVs after removing only `wall_time_s` and `cpu_time_s`; all remaining headers, rows, values, and ordering must match exactly. Compare runtime settings field-by-field; the expected output-directory and post-change code/build provenance differences are recorded, not silently discarded. Trace hash, full simulation arguments other than outDir, routing order, channel behavior, and resolved legacy interpolation must match. Any deterministic output difference fails B2; do not retry.

## Budget and stop rule

This single invocation costs exactly 3 protocol variants. Pre-B2 spend is 11/300 (B0 3 + B1 5 + B1′ fresh confirmation 3); B2 brings cumulative spend to **14/300**, leaving 286. Offline generator validation costs zero. The target-length timing probe is not authorized by this continuation: first clarify the pilot cap's unit as a maximum number of protocol variants (not elapsed time, frame count, packet count, or bare invocations). No timing probe, 7C, or campaign is authorized here.
