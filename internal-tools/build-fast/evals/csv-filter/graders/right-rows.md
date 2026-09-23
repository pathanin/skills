---
type: regex
pattern: '^"?A10(02|04|07|08|10|12|14)"?,'
flags: m
match: "count:7"
target:
  source: file
  path: big_orders.csv
---
