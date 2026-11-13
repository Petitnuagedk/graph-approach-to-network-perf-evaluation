# A0-R patch comparison against the current dirty timeline file

Compared current `/home/hledirach/Documents/YaDyGaGa/yadygaga/timelineBlockGenerator.py` (SHA-256 `49506167cf764705e4e3fc7d3944d070dc2602c69b8ae250fcf3fc6e851591f5`) with the isolated A0-R version (SHA-256 `79c7db13016b6225973650ec561b343e7223b241ae0039bacacd1e810e8d04c6`). The current file matches the current repository HEAD blob; `git status` and `git diff` show no present unstaged edit for this file. Relative to A0's pinned clean commit `51b01ac7faa78a494c3baedc560d658f384afe09`, the file contains the following block-placement changes:

```diff
@@ stability-derived up-block target
         up_blocks = max(min_up_blocks, min(max_up_blocks, up_blocks))
+        # A run requires a separating down frame except at one boundary.
+        up_blocks = min(up_blocks, down_count + 1)

@@ positive run-size split
-            parts = max(1, parts)
+            parts = max(1, min(parts, total))
```

**Yes: both hunks touch the block-placement construction rewritten by A0-R.** The patch replaces the stable even split/placement algorithm with seeded positive compositions and valid run-boundary placement. It retains the stability-derived run target but does not silently cap it: when the target exceeds `down_count + 1`, it raises `ValueError` because exact requested quota and run count cannot both be satisfied. The positive composition directly guarantees each up/down block is nonempty, replacing the dirty `_split_counts` defensive clamp.

The full clean-HEAD-to-A0-R patch, including the timeline-method replacement, is [yadygaga_a0r.patch](yadygaga_a0r.patch). The complete unified diff of the current dirty timeline file versus the A0-R implementation is [timeline_dirty_vs_a0r.patch](results/timeline_dirty_vs_a0r.patch), SHA-256 `66b8d83d491fd57ce94a505596e8a6e89f896831eadf303b1cd04573eb0681b9`. Other differences are the expected full method replacement plus local RNG changes, not unrelated repository edits. The dirty checkout was not edited or imported during A0-R.
