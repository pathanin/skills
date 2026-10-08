#!/bin/bash
# Six independent unit modules behind one pinned registry contract. Each piece is one new file
# plus its existing test file, so a swarm should run 6 Haiku builders. registry.py and the
# tests are checksummed: a builder that "fixes" the shared contract shows up as CHANGED.
set -e
git init -q .
mkdir -p unitconv tests docs
touch tests/__init__.py

cat > unitconv/__init__.py <<'EOF'
"""Unit conversion. Each unit kind lives in its own module and registers itself on import."""
EOF

cat > unitconv/registry.py <<'EOF'
"""Converter registry. CONTRACT v1: every unit module depends on this exact API. Do not edit."""
_CONVERTERS = {}


def register(kind, src, dst, fn):
    """Register fn(value) -> float converting a value of `kind` from unit src to unit dst."""
    if src == dst:
        raise ValueError("src and dst must differ")
    key = (kind, src, dst)
    if key in _CONVERTERS:
        raise ValueError(f"duplicate converter {key}")
    _CONVERTERS[key] = fn


def convert(kind, value, src, dst):
    if src == dst:
        return float(value)
    try:
        fn = _CONVERTERS[(kind, src, dst)]
    except KeyError:
        raise KeyError(f"no converter for {kind}: {src} -> {dst}") from None
    return fn(value)


def pairs(kind):
    return sorted((s, d) for k, s, d in _CONVERTERS if k == kind)


def kinds():
    return sorted({k for k, _, _ in _CONVERTERS})
EOF

cat > unitconv/all.py <<'EOF'
"""Import every unit module so all converters are registered."""
from unitconv import length, mass, temperature, volume, speed, data  # noqa: F401
EOF

cat > unitconv/cli.py <<'EOF'
"""Usage: python3 -m unitconv.cli KIND VALUE SRC DST"""
import sys

import unitconv.all  # noqa: F401
from unitconv.registry import convert


def main(argv):
    kind, value, src, dst = argv
    print(f"{convert(kind, float(value), src, dst):.6g}")


if __name__ == "__main__":
    main(sys.argv[1:])
EOF

cat > docs/units.md <<'EOF'
# Unit modules

Each kind is one module, `unitconv/<kind>.py`. On import it calls
`unitconv.registry.register(kind, src, dst, fn)` once for **every ordered pair of distinct
units** of that kind (n units -> n*(n-1) converters). A module imports only
`unitconv.registry`, never another unit module. `registry.py` is a pinned contract: do not edit it.

| kind (module) | units | definitions |
|---|---|---|
| `length` | `m`, `km`, `mi`, `ft` | 1 km = 1000 m; 1 mi = 1609.344 m; 1 ft = 0.3048 m |
| `mass` | `kg`, `g`, `lb`, `oz` | 1 g = 0.001 kg; 1 lb = 0.45359237 kg; 1 oz = 1/16 lb |
| `temperature` | `C`, `F`, `K` | F = C * 9/5 + 32; K = C + 273.15 |
| `volume` | `l`, `ml`, `gal`, `cup` | 1 ml = 0.001 l; 1 gal (US) = 3.785411784 l; 1 cup = 1/16 gal |
| `speed` | `mps`, `kph`, `mph`, `knot` | 1 kph = 1000/3600 mps; 1 mph = 1609.344/3600 mps; 1 knot = 1852/3600 mps |
| `data` | `B`, `KB`, `MB`, `KiB`, `MiB` | 1 KB = 1000 B; 1 MB = 1000000 B; 1 KiB = 1024 B; 1 MiB = 1048576 B |
EOF

gen_test() {  # kind, python list of units, then "src dst value expected" lines
  local kind=$1 units=$2; shift 2
  {
    echo "import itertools"
    echo "import unittest"
    echo
    echo "import unitconv.$kind  # noqa: F401  (registers on import)"
    echo "from unitconv.registry import convert, pairs"
    echo
    echo "UNITS = $units"
    echo
    echo
    echo "class Test$(echo "${kind^}")(unittest.TestCase):"
    echo "    def test_every_pair_registered(self):"
    echo "        self.assertEqual(pairs(\"$kind\"), sorted(itertools.permutations(UNITS, 2)))"
    echo
    echo "    def test_values(self):"
    for line in "$@"; do
      set -- $line
      echo "        self.assertAlmostEqual(convert(\"$kind\", $3, \"$1\", \"$2\"), $4, places=6)"
    done
    echo
    echo "    def test_round_trip(self):"
    echo "        for a, b in itertools.permutations(UNITS, 2):"
    echo "            self.assertAlmostEqual(convert(\"$kind\", convert(\"$kind\", 37.5, a, b), b, a), 37.5, places=6)"
  } > "tests/test_$kind.py"
}
gen_test length '["m", "km", "mi", "ft"]' "mi km 1 1.609344" "ft m 10 3.048" "km mi 5 3.1068559611866697"
gen_test mass '["kg", "g", "lb", "oz"]' "lb kg 1 0.45359237" "oz g 1 28.349523125" "kg lb 2 4.409245243697551"
gen_test temperature '["C", "F", "K"]' "C F 100 212" "F C -40 -40" "K F 0 -459.67" "F K 32 273.15"
gen_test volume '["l", "ml", "gal", "cup"]' "gal l 1 3.785411784" "cup ml 1 236.5882365" "l cup 1 4.226752837730867"
gen_test speed '["mps", "kph", "mph", "knot"]' "kph mps 36 10" "knot kph 1 1.852" "mph knot 1 0.8689762419006479"
gen_test data '["B", "KB", "MB", "KiB", "MiB"]' "KiB B 1 1024" "MB KB 1 1000" "MiB KB 1 1048.576" "KB KiB 1 0.9765625"

cat > tests/test_all.py <<'EOF'
import subprocess
import sys
import unittest

import unitconv.all  # noqa: F401
from unitconv.registry import kinds, pairs


class TestAll(unittest.TestCase):
    def test_every_kind_registered(self):
        self.assertEqual(kinds(), ["data", "length", "mass", "speed", "temperature", "volume"])
        self.assertEqual(sum(len(pairs(k)) for k in kinds()), 12 + 12 + 6 + 12 + 12 + 20)

    def test_cli(self):
        out = subprocess.run([sys.executable, "-m", "unitconv.cli", "temperature", "100", "C", "F"],
                             capture_output=True, text=True, check=True).stdout
        self.assertEqual(out.strip(), "212")
EOF

PROTECTED="unitconv/registry.py tests/test_*.py docs/units.md"

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
