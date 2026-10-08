#!/bin/bash
# Three mechanical pieces (CSV export, date filter, currency formatting) and one debugging piece
# whose root cause the prompt doesn't give: monthly totals are "sometimes a cent low".
# Cause: totals.py truncates float(amount) * 100 with int(), so 0.29 -> 28 cents.
# Right model split: the three mechanical pieces on haiku, the debugging piece on sonnet or opus.
set -e
git init -q .
mkdir -p ledger tests data
touch tests/__init__.py

cat > ledger/__init__.py <<'EOF'
"""Household ledger: load entries, total them per month, print or export."""
EOF

cat > ledger/entries.py <<'EOF'
import csv
from datetime import date


def load(path):
    """Read date,description,amount rows. amount is a decimal string like "12.10" or "-3.5"."""
    with open(path, newline="") as f:
        return [{"date": date.fromisoformat(r["date"]), "description": r["description"],
                 "amount": r["amount"]} for r in csv.DictReader(f)]
EOF

cat > ledger/totals.py <<'EOF'
from collections import defaultdict


def monthly_cents(entries):
    """Total each month's amounts in integer cents: {"YYYY-MM": cents}."""
    totals = defaultdict(int)
    for e in entries:
        cents = int(float(e["amount"]) * 100)
        totals[e["date"].strftime("%Y-%m")] += cents
    return dict(totals)
EOF

cat > ledger/cli.py <<'EOF'
"""Usage: python3 -m ledger.cli FILE [--since YYYY-MM-DD] [--csv] [--symbol S]"""
import argparse

from ledger.currency import format_amount
from ledger.entries import load
from ledger.export_csv import to_csv
from ledger.filters import since
from ledger.totals import monthly_cents


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("file")
    p.add_argument("--since")
    p.add_argument("--csv", action="store_true")
    p.add_argument("--symbol", default="$")
    a = p.parse_args(argv)
    entries = load(a.file)
    if a.since:
        entries = since(entries, a.since)
    totals = monthly_cents(entries)
    if a.csv:
        print(to_csv(totals), end="")
    else:
        for month in sorted(totals):
            print(month, format_amount(totals[month], a.symbol))


if __name__ == "__main__":
    main()
EOF

cat > SPEC.md <<'EOF'
# Missing modules

`ledger/cli.py` already imports these. Each is its own file.

- `ledger/export_csv.py`: `to_csv(totals)` takes `{"YYYY-MM": cents}` and returns a string: a
  `month,total` header, then one row per month sorted by month, total as a plain decimal with two
  places (`-3.50`, `1234.05`; no symbol, no thousands separator). Lines end in `\n`, including
  the last.
- `ledger/filters.py`: `since(entries, date_str)` keeps entries on or after the ISO date
  `date_str`, in their original order.
- `ledger/currency.py`: `format_amount(cents, symbol="$")` returns e.g. `$1,234.50`; negatives
  are `-$3.00`; zero is `$0.00`.
EOF

cat > data/sample.csv <<'EOF'
date,description,amount
2026-01-03,coffee,0.29
2026-01-09,groceries,57.10
2026-02-01,rent,-1200.00
2026-02-14,refund,19.99
EOF

cat > tests/test_export_csv.py <<'EOF'
import unittest

from ledger.export_csv import to_csv


class TestToCsv(unittest.TestCase):
    def test_rows(self):
        self.assertEqual(to_csv({"2026-02": -350, "2026-01": 123405}),
                         "month,total\n2026-01,1234.05\n2026-02,-3.50\n")

    def test_small_and_empty(self):
        self.assertEqual(to_csv({"2026-03": 5}), "month,total\n2026-03,0.05\n")
        self.assertEqual(to_csv({}), "month,total\n")
EOF

cat > tests/test_filters.py <<'EOF'
import unittest
from datetime import date

from ledger.filters import since

E = [{"date": date(2026, 1, d), "description": str(d), "amount": "1"} for d in (9, 3, 5, 1)]


class TestSince(unittest.TestCase):
    def test_inclusive_and_ordered(self):
        self.assertEqual([e["description"] for e in since(E, "2026-01-05")], ["9", "5"])

    def test_none_match(self):
        self.assertEqual(since(E, "2027-01-01"), [])
EOF

cat > tests/test_currency.py <<'EOF'
import unittest

from ledger.currency import format_amount


class TestFormatAmount(unittest.TestCase):
    def test_formats(self):
        self.assertEqual(format_amount(123450), "$1,234.50")
        self.assertEqual(format_amount(-300), "-$3.00")
        self.assertEqual(format_amount(0), "$0.00")
        self.assertEqual(format_amount(5, "€"), "€0.05")
        self.assertEqual(format_amount(-123456789), "-$1,234,567.89")
EOF

cat > tests/test_totals.py <<'EOF'
import unittest
from datetime import date

from ledger.totals import monthly_cents


def entries(*amounts):
    return [{"date": date(2026, 1, 1), "description": "x", "amount": a} for a in amounts]


class TestMonthlyCents(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(monthly_cents(entries("1.00", "2.50")), {"2026-01": 350})

    def test_never_a_cent_low(self):
        # Reported by users: some months come out a cent low.
        for a, cents in [("0.29", 29), ("0.57", 57), ("1.15", 115), ("4.35", 435), ("-0.29", -29),
                         ("19.99", 1999), ("1155.10", 115510), ("-3.5", -350), ("2", 200)]:
            self.assertEqual(monthly_cents(entries(a)), {"2026-01": cents}, a)

    def test_cli_end_to_end(self):
        import subprocess
        import sys
        out = subprocess.run([sys.executable, "-m", "ledger.cli", "data/sample.csv", "--since",
                              "2026-01-05", "--csv"], capture_output=True, text=True, check=True).stdout
        self.assertEqual(out, "month,total\n2026-01,57.10\n2026-02,-1180.01\n")
EOF

PROTECTED="tests/test_*.py SPEC.md ledger/cli.py data/sample.csv"

# --- shared tail: acceptance script, protected-file checksums, initial commit ---
cat > check.sh <<'EOF'
#!/bin/bash
# Acceptance check. Run from the repo root as the last step: ./check.sh > check-output.txt
cd "$(dirname "$0")"
out=$(python3 -m unittest discover -s tests -t . 2>&1); rc=$?
echo "$out" | tail -n 25
ran=$(echo "$out" | grep -oE '^Ran [0-9]+' | grep -oE '[0-9]+')
if [ "$rc" -eq 0 ]; then echo "CHECK RESULT: PASS (${ran:-0} tests)"; else echo "CHECK RESULT: FAIL (${ran:-0} tests)"; fi
if sha256sum --quiet -c .protected.sha256 >/dev/null 2>&1; then echo "protected files: intact"; else echo "protected files: CHANGED"; fi
echo "worktrees left: $(( $(git worktree list | wc -l) - 1 ))"
echo "agent branches left: $(git branch --list 'worktree-*' '*agent*' 'swarm/*' | wc -l)"
EOF
chmod +x check.sh
sha256sum $PROTECTED > .protected.sha256
git add -A
git commit -qm "Initial import"
