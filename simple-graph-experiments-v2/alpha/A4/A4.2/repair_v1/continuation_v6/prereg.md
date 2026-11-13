# A4.2 continuation-v6 addendum — unrestricted runtime continuation

Registered 2026-10-14 after continuation-v4 stopped at row 64 under the resource guard. The user explicitly authorized allowing each remaining A4.2 process to run for the time it needs, without the 3,600-second timeout and without stopping on the prior swap/memory guard.

Rows 1-63 remain immutable and are reused read-only from continuation-v2. Rows 64-90 are the only eligible new launches, each at most once. A4.3 remains prohibited.

The fixed simulation settings, serial execution, no retry of any consumed attempt, and append-only accounting remain in force. This addendum supersedes only the per-run runtime timeout and resource-guard stop for rows 64-90.
