---
type: llm
focus:
  source: file
  path: text.py
---

PASS if slugify takes max_length defaulting to None, returns the unchanged slug when it is None, never returns more than max_length characters otherwise, cuts at the last hyphen within the limit when one exists, and never leaves a trailing hyphen.
FAIL if any of those fails, or if the default behavior changed.
