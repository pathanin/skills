---
type: regex
pattern: '(fonts\.googleapis|@import|@font-face|linear-gradient|radial-gradient|box-shadow|backdrop-filter|--[a-z][a-z0-9-]*\s*:)'
match: not_contains
target:
  source: file
  path: stats.html
---
