# Phase 6A preregistration — written before examining Phase 6 packet-level results

This preregistration operationalizes the user-specified predictions and refutation criteria. Do not revise thresholds after inspecting outcomes. Phase 6 outputs only; prior campaign trees remain read-only.

## H1 — buffering / delayed delivery

**Prediction:** requests held in AODV's queue, IP/MAC queues, or MAC retries produce a material fraction of deliveries either during an oracle-down interval or more than one second after application transmission.

**Support criterion:** for AODV, at least 10% of uniquely received offered packets in at least two of the three tested settings are received while the S–R link is below the operational receive threshold, or have end-to-end delay greater than 1.0 s. Record both conditions separately and their union; do not count one packet twice in the union.

**Refutation criterion:** in all three settings, both fractions are at most 1.0%, and no corresponding AODV request-queue drops / packet trace evidence of queue-held delivery is observed.

**Otherwise:** undecided. Report OLSR and static figures descriptively, but H1's primary classification is based on AODV.

## H2 — oracle/traffic-window/usable-loss mismatch

**Prediction:** using the actual offered-traffic interval and thresholded, interpolated channel state changes effective uptime materially relative to the all-frame binary oracle, and reduces the positive raw-PDR-minus-oracle gap.

**Definitions fixed before analysis:** operational link-up threshold is received power at or above the configured Wi-Fi receiver sensitivity (20 dBm transmit power minus loss; sensitivity from the ns-3 PHY configuration). Use the actual client-active half-open interval. Integrate continuous interpolated channel state over that interval; separately calculate state at packet Tx and Rx timestamps.

**Support criterion:** traffic-window/interpolation adjustment differs from the all-60-frame uptime by at least 0.05 in at least two settings, and removes at least half the positive static PDR-minus-uptime gap in at least two settings.

**Refutation criterion:** the adjustment is at most 0.01 in all settings, or it fails to reduce the positive gap in all settings.

**Otherwise:** undecided. Distinguish a corrected oracle from any remaining unexplained gap.

## H3 — duplicate receive counting

**Prediction:** aggregate sink receive counters may count duplicate application sequence numbers, causing `app_rx_pkts` to exceed unique delivered datagrams.

**Support criterion:** any tested protocol/settings has total sink packet callbacks greater than unique sequence numbers accepted at the sink; quantify duplicate count and affected PDR.

**Refutation criterion:** total receives equal unique sequence count for every protocol in every 6A setting, with sequence-number accounting validated against offered application sequence numbers.

**Otherwise:** undecided only if the per-packet trace is incomplete or sequence identity cannot be matched.

## H4 — static-baseline implementation losses

**Prediction:** static oracle-route delivery losses occur despite an operational S–R channel, particularly in the first second of each up-run, consistent with ARP/route installation timing or boundary scheduling.

**Support criterion:** at least 80% of unrecovered static offered packets are sent while the channel is operational but are absent at the sink, and at least 80% of these losses fall in the first second of an operational up-run.

**Refutation criterion:** at most 10% of static losses are sent during an operational up interval, or at most 10% of operational-up losses fall in the first second; remaining losses are attributable to down-state transmission or independently measured Wi-Fi failure.

**Otherwise:** undecided. Use the all-up controls in 6B to verify baseline capability; do not describe static as a ceiling unless its gate passes.

## 6A batch design fixed in advance

- Fifteen stored line-topology realizations, three cells × five DG seeds, one replay epoch each.
- Conditions: path_life 0.5 / stability 0.0 / persistency 0.75; path_life 0.7 / stability 0.8 / persistency 0.75; path_life 0.9 / stability 0.8 / persistency 0.75.
- Same Phase 5 DG seeds/traces; OLSR, AODV, static variants; `--dump-routes` and packet-level logging enabled. Preserve Phase 5 files and configs.
- Exact worktree result: 15 ns-3 scenario invocations, each containing 3 variants = 45 protocol replay variants. This is below the 300-run batch threshold whichever count is used.
- No outcome data will be inspected until the event schema, prediction/refutation criteria, and run list have been saved here.
