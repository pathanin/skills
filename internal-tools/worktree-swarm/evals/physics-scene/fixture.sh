#!/bin/bash
# A visual case: seven modules of a ball-physics sim with a ray-traced renderer (template/), built by
# the swarm from SPEC.md. check.sh runs the tests, renders out/sheet.png + out/final.png, and checks the
# physics metrics. reference/ holds a known-good implementation for calibration; it is not copied.
set -e
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
git init -q .
cp -r "$here/template/." .
find . -name __pycache__ -prune -exec rm -rf {} +
cat > check.sh <<'EOF'
#!/bin/bash
# Acceptance check. Run from the repo root as the last step: ./check.sh > check-output.txt
cd "$(dirname "$0")"
out=$(python3 -m unittest discover -s tests -t . 2>&1); rc=$?
echo "$out" | tail -n 25
ran=$(echo "$out" | grep -oE '^Ran [0-9]+' | grep -oE '[0-9]+')
if [ "$rc" -eq 0 ]; then echo "CHECK RESULT: PASS (${ran:-0} tests)"; else echo "CHECK RESULT: FAIL (${ran:-0} tests)"; fi
if metrics=$(timeout 600 python3 make_movie.py 2>&1) && [ -s out/sheet.png ] && [ -s out/final.png ]; then
  echo "movie: ok $metrics"
  python3 - <<'PY'
import json
m = json.load(open("out/metrics.json"))
ok = m["finite"] and m["energy_max_ratio"] <= 1.02 and m["max_penetration"] <= 0.03 and m["energy_end"] < m["energy_start"]
print("physics:", "ok" if ok else "BAD", json.dumps(m))
PY
else
  echo "movie: FAILED"; echo "$metrics" | tail -n 5
fi
if sha256sum --quiet -c .protected.sha256 >/dev/null 2>&1; then echo "protected files: intact"; else echo "protected files: CHANGED"; fi
echo "worktrees left: $(( $(git worktree list | wc -l) - 1 ))"
echo "agent branches left: $(git branch --list 'worktree-*' '*agent*' 'swarm/*' | wc -l)"
EOF
chmod +x check.sh
printf 'out/\n__pycache__/\n' > .gitignore
sha256sum ballpit/world.py ballpit/vec.py ballpit/png.py ballpit/sim.py make_movie.py SPEC.md tests/test_*.py > .protected.sha256
git add -A
git commit -qm "Initial import"
