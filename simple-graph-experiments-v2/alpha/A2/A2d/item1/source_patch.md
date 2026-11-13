# A2d item 1 exact source patch

This is the apply-ready unified diff from the registered A0-R2 `yadygaga/frameGenerator.py` to this item's isolated patched source. The payload is gzip-compressed then base64-encoded to keep it text-safe; its decompressed bytes are a standard unified diff.

- Base file SHA-256: `e84971f89cb966a574bf447ce8135c0c241b407be14e5066db2f82f3c2ec6b4b`.
- Result file SHA-256: `346ee8bc8399fbe1fa010927082a34c9156f56283512ecafe00d69d573a1b6bf`.
- Decompressed unified patch SHA-256: `16052d4777996aa6e7b3a09cf5de7fac6707242e340dfa74d669db58dd66ffc7`.
- Encoded patch payload SHA-256: `a8875c6d8ebecac888e352daa341ab520844c2d57e2dd7dd8e3ad852b073cb12`.
- Apply helper SHA-256: `3be27c8d64d8e1dc6b65b414f32bf8813719ed0936ad77ec9f10adb848ae2536`.

The helper accepts the root of a **separate writable copy** of the A0-R2 source tree. It performs `patch --dry-run` first and only then applies the patch. Do not pass the protected historical A0-R2 tree; the validated item-specific result already exists at `source/yadygaga/frameGenerator.py`.

The patch was reconstructed from the byte-exact `diff -U0` between the registered baseline and result files. Its decompressed SHA matched the fresh diff, and `patch --dry-run -p1` reported a clean application against the baseline without modifying it. No experiment was rerun.
