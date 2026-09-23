---
type: regex
pattern: '(requirements\.txt|README|(^|/)test_[^/]*$|_test\.py$|pyproject\.toml|setup\.py|\.venv/)'
flags: m
match: not_contains
target: files
---
