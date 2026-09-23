---
type: llm
focus:
  source: file
  path: text.py
---

Check these by reading the code:
- slugify("hello world foo", max_length=11) == "hello-world" (a cut that lands exactly on a word boundary keeps that whole word)
- slugify("hello world foo", max_length=8) == "hello"
- slugify("helloworld", max_length=5) == "hello" (no hyphen available, so a mid-word cut is allowed)
- slugify("hello world") == "hello-world" (max_length defaults to None and changes nothing)
- the result never ends with a hyphen and is never longer than max_length

PASS only if every item holds.
FAIL if any item fails; say which one.
