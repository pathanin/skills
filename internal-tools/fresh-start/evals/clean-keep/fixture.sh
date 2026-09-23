#!/bin/bash
# A small, clean, well-tested function. The right outcome is to keep it and add the option.
set -e
git init -q .
cat > text.py <<'PY'
import re
import unicodedata


def slugify(title):
    """Lowercase ASCII slug: 'Héllo, World!' -> 'hello-world'."""
    text = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-")
    return text.lower()
PY
cat > test_text.py <<'PY'
import unittest
from text import slugify


class SlugifyTest(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(slugify("Hello, World!"), "hello-world")

    def test_accents(self):
        self.assertEqual(slugify("Héllo Wörld"), "hello-world")

    def test_collapses_separators(self):
        self.assertEqual(slugify("  a -- b__c  "), "a-b-c")

    def test_empty(self):
        self.assertEqual(slugify("!!!"), "")


if __name__ == "__main__":
    unittest.main()
PY
git -c user.name=dev -c user.email=dev@example.com add -A
git -c user.name=dev -c user.email=dev@example.com commit -qm "Add slugify"
