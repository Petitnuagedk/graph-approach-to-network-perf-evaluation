# Phase 7B′ preregistration — deadline-qualified usable-up delivery reference

**Written 2026-10-08, after inspection of B1 results.** This is a post-B1 exploratory amendment and does not replace, reinterpret, or relax the original B1 preregistration. B1's absolute PDR-versus-usable-uptime tolerance remains 0.05; its failure is retained as a failure. The B1′ offline calculation has zero simulator variants and is exploratory only. A passing offline result is not a passed gate until the fresh confirmation specified below also passes.

## Question and frozen definition

B1's aggregate PDR counts packets delivered after they may have waited through an unusable interval, so B1′ asks whether a deadline-qualified delivery fraction for packets sent in usable-up intervals is a closer reference to traffic-window usable uptime.

For each B1 alternating S–R run, match each application TX and RX by packet `sequence` in `packets_static.csv`. Use the TX/RX timestamps in the corresponding `times_static.csv` as the event-time source; before calculating, require event-kind timestamp streams to match the sequence-bearing packet log exactly in order and at the recorded 1 μs precision. Use `usable_connected` on the TX record to identify whether the packet was sent during a usable-up interval. The per-run statistic is:

$$
Q_{\tau} = \frac{\#\{\text{all offered TX packets sent while usable-connected and received by }t_{TX}+\tau\}}{\#\{\text{all offered application TX packets in the traffic window}\}}.
$$

A packet qualifies only if its matching RX exists, `0 ≤ t_RX − t_TX ≤ τ`, and the TX event has `usable_connected=1`. Each sequence counts at most once. Packets sent outside usable-up intervals and packets delivered after the deadline do not enter the numerator. The denominator remains all offered TX packets, so this statistic estimates the fraction of offered traffic that both originates in usable-up time and completes within the fixed deadline; it is compared directly with C++ traffic-window usable uptime, not with PDR.

## Frozen numerical criteria

- Deadline: **τ = 0.050 s** (50 ms), fixed before this B1′ computation. It is approximately six 8.192-ms application packet intervals at the already-recorded 1 Mbps / 1,024-byte B1 probe setting; it is not selected from observed delivery delays.
- Per-run acceptance: **absolute difference `|Qτ − Uusable| ≤ 0.05`**, where `Uusable` is the saved C++ traffic-window usable-uptime value. Do not change τ, denominator, interval labels, or tolerance after computing the offline result.
- Integrity requirements: TX and RX event-time streams from `times_static.csv` match `packets_static.csv` in order and count; packet sequence IDs are unique per TX and at most one RX is counted per sequence; every qualifying delay is nonnegative; and C++ usable uptime matches the existing independent Python recomputation to absolute error ≤ **1e-9**.
- Evaluate all three existing B1 down-loss settings independently (125, 200, and 1,000,000 dB). Report numerator, all-TX denominator, `Qτ`, usable uptime, absolute difference, RX count excluded for exceeding τ, and integrity checks for each. No pooling across runs.

## Fresh confirmation required to pass

The saved B1′ offline result is exploratory regardless of outcome. If and only if all three offline B1′ runs satisfy the frozen criteria and integrity checks, run one fresh alternating S–R confirmation batch consisting of exactly three static-only `graph-run` invocations at down-loss 125, 200, and 1,000,000 dB (3 protocol variants total). Reuse the frozen 60-frame alternating fixture and all other B1 traffic/channel settings, including v2/no interpolation, 1 Mbps, 1,024-byte packets, seed 42, 1 fps, and zero warm-up; write outputs to new B1′ run directories and preserve configs, exact invocation arguments, hashes, and raw event logs. Apply the same frozen `Qτ` and integrity criteria to each fresh run. B1′ can be reported as passed only if all three fresh runs pass; a failure stops the gate with no retries.

If the offline calculation fails, do not spend the three confirmation variants. If the fresh batch is authorized by the offline pass, the Phase 7 spend will be **11/300** (8 already spent + 3 confirmation variants). This B1′ does not authorize B2, a timing probe, 7C, or a campaign; those remain separately gated.

## Interpretation limits

Because this gate and its thresholds were written after inspection of B1, the existing-data result is exploratory and cannot be represented as preregistered confirmation. Even a successful fresh confirmation supports only this specific 60-frame alternating S–R probe, fixed traffic configuration, and deadline-qualified reference; it does not rescue or erase original B1's failed aggregate-PDR criterion and does not establish population-level calibration or protocol performance.
