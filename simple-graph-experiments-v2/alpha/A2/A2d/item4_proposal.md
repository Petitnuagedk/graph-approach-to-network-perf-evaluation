# A2d item 4 — stability/life decoupling proposal only

**Status: proposal; no implementation, source change, or experiment is authorized here.** This note is after A2a/A2b/A2c results and explicitly takes the A2a feasibility map into account.

## Mathematical constraint

For a finite Boolean trace with exactly U up frames, D=F−U down frames, and K positive up-runs, necessarily `1 <= K <= min(U, D+1)`. This support boundary is structural. No reparameterization can make every `(U,K)` combination feasible while retaining exact uptime, binary states, and nonempty runs; the triangular boundary can only be represented more honestly, not removed.

For example at F=120 and life=.9, U=108 and D=12, so K can be at most 13. A high requested run count is impossible regardless of how “stability” is named.

## Candidate interface

If approved, expose independent primitive inputs `(target_up_count U, target_up_runs K)` rather than using a single stability slider to determine K from U. Construct exact U and K only when `K <= min(U,D+1)`; otherwise reject with a typed infeasibility result (no clamping, no silent reduction). Report `mean_up_run=U/K` and derive the legacy-equivalent stability for comparison as `s = 1 - (K-1)/(U-1)` for U>1; define the U<=1 cases explicitly. Keep down-run allocation sampled from the registered exact support, with total transitions reported, not promised fixed.

This decouples the *user controls* (uptime and run count), but not the mathematical feasible set. A second, experimental option would add a transition-intensity parameter to sample among feasible down-run counts; this would need its own distributional study and is not recommended until the direct `(U,K)` interface is validated.

## Recommendation and approval needed

Recommendation: if the goal is independent control, prototype the explicit `(U,K)` interface in a new isolated source copy, preserve the current `stability` argument as a legacy adapter, and test infeasible requests as explicit failures. Do not claim that this eliminates the physical feasibility boundary. User approval is required before any code, thresholds, or test stage are created. No A3, ns-3, protocol variants, or changes to A0/A1/A2a-A2d results are included.
