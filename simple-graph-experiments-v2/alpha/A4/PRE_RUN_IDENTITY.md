# A4 pre-run identity record

Recorded after offline validation and before any A4 protocol variant.

- Preregistration: `prereg.md` SHA-256 `159c1d0a96cf99adec47ead45df186d34706a6fc6b0c2f5a6f36d47bc6f23cc8`.
- Frozen runner: `a4.py` SHA-256 `1377ceced00147cfc371cc64d1916298b84892dfe218560a920c4f0fadebf013`.
- Frozen dispatcher: `run.sh` SHA-256 `9eb7ca51244a2213ee2694e6b7eb932a6c7d8140a73b849d05e5f44ade8a6754`.
- Protected simulator source, read-only: `/home/hledirach/Documents/sp1-sp2/scratch/graph-run.cc` SHA-256 `ef8e5412a23100136449f1b44bbfb18be1575a659c5f1a889be78f0808bdbdb6`.
- A1 graph manifest SHA-256 `b1b02780436404591f6b218b1eb465da7a7ef661bc9ee86df54cb8c9fe4649d7`; covariates SHA-256 `51895a726c14bbb013b2996b7aa14b37a1a8103ee052f70ab1564c4ac3de8759`.
- Offline checks passed: all 39 A1 graph identities/edge hashes loaded; N=42 and N=162 all-up matrices validated for 120 frames against their source edge lists; C++ `llround` counts checked; stored A3b OLSR/AODV fixture outputs passed V1/V2/V3 schema and conservation validators.
- Python 3.14.4 syntax compilation and shell syntax validation passed. No protocol variants had been attempted at record time.

No simulator source, A1 artifact, or historical stage result was modified.
