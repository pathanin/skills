---
type: llm
---

PASS if the final reply says the existing slugify was kept (the old version won, or the fresh version was not clearly better), gives a reason, and describes the only change to it as adding max_length.
FAIL if the reply reports choosing a fresh or hybrid version, or says it also reworked the existing lines: renamed variables, reformatted, reordered, simplified, or did a "light rewrite" or "cleanup". Also FAIL if it never says which version was kept.
