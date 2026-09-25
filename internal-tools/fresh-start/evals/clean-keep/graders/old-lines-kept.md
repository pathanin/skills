---
type: regex
pattern: 'text = unicodedata\.normalize\("NFKD", title\)\.encode\("ascii", "ignore"\)\.decode\(\)\n[ \t]+text = re\.sub\(r"\[\^a-zA-Z0-9\]\+", "-", text\)\.strip\("-"\)'
target:
  source: file
  path: text.py
---
