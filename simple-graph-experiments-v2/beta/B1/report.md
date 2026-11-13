# B1 adapted report

## Status amendment — 2026-11-13

A4.5 is complete and supplies both required N=42 seed-42 static reference rows. The user authorized B1, and the executable harness is [run_b1.py](run_b1.py). Results are written to `result.json` and the per-protocol run directories.

## B1 result — 2026-11-13

**PASS — 2/2 protocol comparisons.** The fresh AODV and OLSR runs matched their A4.5 references exactly for configuration identity, the F420 frame SHA-256, probe PDR, background median PDR, control-packet mean/max/Gini, and control-byte mean/max/Gini. The shared frame hash was `12926dab5149260032531d8bf5715b6efa75b32a0b2d6a73c21f5dc709ad44b2`.

No tolerance, substitution, retry, or sweep was used. The result is recorded in [result.json](result.json) and each protocol's `comparison.json`. B1 passes its gate; B2 is the next stage and requires its own preregistration/authorization.

B1 is **BLOCKED** and was not launched. The required A4.5 seed-42 static records for N=42 AODV and OLSR do not exist. A4.5's 30 attempts stopped before simulator launch at the zero-swap environment guard.

The registered exact comparison remains: configuration hash, trace/frame hash, probe PDR, background median PDR, and control totals must match the A4.5 records. No comparison was possible and no Beta result was produced.

No simulator, generator, or protocol run was launched by B1.

## Historical-status clarification — 2026-11-13

The preceding blocked text is retained as historical preparation-stage context and is superseded by the B1 result above. B1 did run after A4.5 completion and passed 2/2 exact comparisons. The authoritative machine-readable result is [result.json](result.json).
