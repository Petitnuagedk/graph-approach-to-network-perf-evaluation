# A4.2 continuation-v3 addendum — resume after guard stop in continuation-v2

Registered 2026-10-14 after continuation-v2 stopped under resource guard. This addendum preserves all prior records and authorizations, including the user decision to continue A4.2 despite checkpoint projection >24 h and the prohibition on A4.3.

## Frozen history preserved

- repair-v1 historical dataset remains immutable.
- continuation-v2 outcomes remain immutable:
  - sequences 1-60 reused successful rows,
  - sequences 61-63 timed out at 3600 s and are consumed attempts,
  - sequence 64 resource-guard blocked due to swap usage,
  - sequences 65-90 marked not attempted because of guard-stop.

No consumed attempt is rerun or relabeled.

## Continuation-v3 scope

Authorize launching only cells that were not launched in continuation-v2 because of the guard stop:

- include sequence 64 exactly once (it was guard-blocked before launch), and
- include sequences 65-90 exactly once.

Total maximum new launches in continuation-v3: 27.

Attempt accounting remains append-only: prior cumulative charge 138/300 after continuation-v2 (135 base + 3 new timeouts). Maximum cumulative charge after continuation-v3 if all 27 launch: 165/300. Per-run resource guard (MemAvailable >= 8 GiB and SwapUsed = 0), serial execution, 3600 s timeout, no retry, and all fixed simulation settings remain binding.

A4.3 remains prohibited.
