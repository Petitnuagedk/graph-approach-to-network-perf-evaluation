# A2d item 1 source diff (reviewable summary)

Base: isolated A0-R2 `yadygaga/frameGenerator.py`, SHA-256 `e84971f89cb966a574bf447ce8135c0c241b407be14e5066db2f82f3c2ec6b4b`.
Result: `source/yadygaga/frameGenerator.py`, SHA-256 `346ee8bc8399fbe1fa010927082a34c9156f56283512ecafe00d69d573a1b6bf`.

This is a human-readable source diff summary, not an apply-ready unified patch. It records the complete changed method surface and algorithmic changes; the complete resulting source is in the isolated source copy and its non-generated file hashes are in `source_manifest.sha256`.

## Changed method surface

```diff
 class FrameGenerator:
     def __init__(self):
         self.path_up_frames = []
         self.path_down_frames = []
+        self.path_up_keys = []
 
     def generateSPCFrames(
         self, limited_G, s, d, trials=1000, p_edge=0.5,
-        pathPersistency=0.0, seed=0,
+        pathPersistency=0.0, seed=0, behavior="legacy",
+        timeline=None, mean_up_duration=4.0,
     ):
+        if behavior == "patched-v3":
+            require a fixed target timeline
+            generateTemporalSPCFrames(...)
+            expose its frames in the existing up/down frame containers
+            return
+        if behavior != "legacy":
+            raise ValueError
+        return _generateSPCFramesLegacy(...)
+
+    def _generateSPCFramesLegacy(...):
+        # Original random edge-sampling/grouping implementation retained.
+
+    @staticmethod
+    def sample_two_state_chain(frames, pi, mean_up_duration, seed):
+        p10 = 1 / mean_up_duration
+        p01 = pi / ((1 - pi) * mean_up_duration)
+        # stationary Bernoulli(pi) initial state; seeded transitions
+
+    @staticmethod
+    def _canonical_shortest_path(graph, source, destination):
+        # reconstruct lexicographically selected shortest route from distance maps
+
+    def generateTemporalSPCFrames(
+        self, limited_G, s, d, timeline, pi, mean_up_duration, seed=0,
+    ):
+        # independently Markov-sample each skeleton edge (deterministic per-edge seeds)
+        # retain raw frames, then project each frame to its target S-R state:
+        #   up target + disconnected raw frame -> add missing canonical route edges
+        #   down target + connected raw frame -> remove deterministic min edge cut
+        # check exact S-R state and return raw/projected frames and corrections
 ```

## Behavioral compatibility

- Default `behavior="legacy"` dispatches to the legacy body and is opt-in-free for existing call sites.
- New per-edge Markov behavior is selected only by explicit `behavior="patched-v3"` and requires the registered fixed timeline.
- Existing legacy body was moved into `_generateSPCFramesLegacy`; it was not replaced by the Markov sampler.
- Source was validated by A2d item 1's 100 compatibility operations; see `results/result.md`.
