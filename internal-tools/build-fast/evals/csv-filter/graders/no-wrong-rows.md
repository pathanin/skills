---
type: regex
pattern: '^"?A10(01|03|05|06|09|11|13)"?,'
flags: m
match: not_contains
target:
  source: file
  path: big_orders.csv
---
