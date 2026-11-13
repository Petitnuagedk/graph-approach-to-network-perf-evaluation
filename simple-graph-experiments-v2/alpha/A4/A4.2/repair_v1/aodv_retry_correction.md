The failing expression evaluated `1 << 31` as a signed `int`; signed overflow is undefined and yielded a negative retry duration on this build. This explains the negative-delay assertion. It does not establish why the route's retry counter accumulated to 32; the exact event/timer interleaving remains unknown. **Append-only type correction:** source review of `aodv-rtable.h` confirms `GetRreqCnt()`/`m_reqCount` are `uint8_t`, not a wider field. The observed 32 is still a valid over-limit counter value; only the earlier addendum's width description was inaccurate.
The AODV library rebuilt with this source is SHA-256 `31eca374d5d519ea348ed500bf9a263ba40cacac259bbd79ac264078f55ca79a`; corrected source SHA-256 `e8f75e0efa0988ae4e039e2ce04eda3e667128f99b035806057412f03b930b5e`. The preserved source snapshot `aodv-routing-protocol.cc.corrected` contains both the failure-only diagnostic logging and the registered bounded correction; its SHA-256 is `e8f75e0efa0988ae4e039e2ce04eda3e667128f99b035806057412f03b930b5e`. The diagnostic-era shared library is retained as `libns3.46.1-aodv-default.so.diagnostic`. Original crash runs and all their status/time records remain failed and are not reclassified.
# AODV retry correction — source rationale and bounded scope

Registered source change under [addendum 3](addendum_3.md). The one-shot diagnostic emitted at simulation time 24.0001 s:

- destination: `10.1.0.155`
- route hop / diameter: `35 / 35`
- RREQ count / configured `RreqRetries`: `32 / 2`
- net traversal time: `2.8 s`
- full-diameter backoff factor: `31`
- computed retry: `−6.01295e18 ns`

The failing expression evaluated `1 << 31` as a signed `int`; signed overflow is undefined and yielded a negative retry duration on this build. This explains the negative-delay assertion. It does not establish why the route's retry counter accumulated to 32; the exact event/timer interleaving remains unknown.

The source correction is limited to the registered two lines of logic:

1. Full-diameter backoff exponent is bounded by `max(RreqRetries−1, 0)` and computed from an unsigned 32-bit one, preventing signed-shift overflow and keeping the delay finite/positive.
2. `RouteRequestTimerExpire` treats counts at or above `RreqRetries` as terminal (`>=`, rather than exact equality), preventing an over-limit counter from bypassing the configured retry cap.

No OLSR, topology, input trace, packet generation, AODV traversal-time constants, retry-limit value, instrumentation, or A4 thresholds were changed. The AODV library rebuilt with this source is SHA-256 `31eca374d5d519ea348ed500bf9a263ba40cacac259bbd79ac264078f55ca79a`; corrected source SHA-256 `e8f75e0efa0988ae4e039e2ce04eda3e667128f99b035806057412f03b930b5e`. The source snapshot carrying diagnostic-only logging is separately retained at `aodv-routing-protocol.cc.corrected`; the diagnostic-only library is retained as `libns3.46.1-aodv-default.so.diagnostic`. Original crash runs and all their status/time records remain failed and are not reclassified.

The corrected AODV pilot is the sole performance check authorized for this source change. A4.2 AODV variants, if launched after a successful pilot and passing projection gate, must use this same corrected AODV build; the report must disclose this implementation change. A failed corrected pilot blocks A4.2 and requires user direction/new registration.
