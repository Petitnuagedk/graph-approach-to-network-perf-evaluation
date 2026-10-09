# Phase 6A instrumentation record

All changes are opt-in under `--dumpRoutes=true`. The legacy output CSV schema and metrics remain unchanged when diagnostics are disabled; a matched regression against the saved Phase 5 line/path-life 0.5, graph 1, replay seed 42 output passed, excluding only nondeterministic `wall_time_s` and `cpu_time_s`.

## Packet event files

For each protocol, the run writes:

- `packets_<protocol>.csv`: one `tx` and one `rx` row per callback. Fields include application sequence number, application send time, event time, end-to-end delay, binary frame-topology connectivity, and thresholded interpolated path feasibility.
- `packet_diagnostics_<protocol>.csv`: offered Tx callbacks, total and unique sink callbacks, duplicate count, app-specific IP no-route/route-error drops, WifiMacQueue drops, general MAC Tx drops, and PHY Tx/Rx drops.
- Existing route tables and `times_<protocol>.csv` remain enabled.

The offered packet sequence at Tx is the one-flow UdpClient Tx-callback ordinal (the callback occurs before ns-3 prepends its sequence header); the sink sequence and original send timestamp are decoded from ns-3's actual `SeqTsHeader`. This is valid for the specified single S→R flow. A test replay produced matching Tx/Rx sequence IDs and nonnegative packet delays; total sink callbacks equaled unique sequence IDs.

`frame_connected` means S–R graph connectivity in the binary frame active at event time. `usable_connected` means a path exists after loss interpolation and the configured receive-power threshold (`20 dBm - loss >= -101 dBm`, equivalently loss ≤121 dB). It describes modeled channel usability, not guaranteed MAC delivery under contention/interference.

## Drop-trace coverage

- IPv4 no-route and route-error events are classified as app traffic using the IPv4 protocol and UDP destination port.
- `WifiMacQueue::Drop` is connected through the non-QoS best-effort queue (`AC_BE_NQOS`); the count covers all queued MAC frames, not only application data. `MacTxDrop` and PHY drop counters are reported separately.
- ns-3 3.46.1's AODV `RequestQueue` is an ordinary internal class with no registered `TypeId` or trace source; its private `Drop()` invokes the queued packet's error callback. No direct request-queue-drop trace is exposed without modifying ns-3 internals, so the Phase 6 results must label that count unavailable rather than infer it from other drops.

The pre-existing scalar `eed_mean_s` calculation is intentionally left unchanged to pass the legacy CSV regression. Phase 6 delay analyses must use the corrected per-packet `delay_s` values from `SeqTsHeader`, not the legacy scalar EED, pending a separately authorized metric change.
