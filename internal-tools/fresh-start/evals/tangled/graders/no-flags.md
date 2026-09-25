---
type: regex
pattern: '\bdone\s*=|\bcost\s*=\s*None\b'
match: not_contains
target:
  source: file
  path: pricing.py
---
