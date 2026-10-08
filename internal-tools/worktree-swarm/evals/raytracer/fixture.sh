#!/bin/bash
# A large build: tinyrt, a ray tracer missing 13 substantial modules (template/), built from SPEC.md.
# check.sh runs the 63 tests, renders out/final.png + out/views.png, and checks the protected files.
# reference/ holds a known-good implementation for calibration; it is not copied.
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
if metrics=$(timeout 900 python3 render.py 2>&1) && [ -s out/final.png ] && [ -s out/views.png ]; then
  echo "render: ok $metrics"
else
  echo "render: FAILED"; echo "$metrics" | tail -n 5
fi
if sha256sum --quiet -c .protected.sha256 >/dev/null 2>&1; then echo "protected files: intact"; else echo "protected files: CHANGED"; fi
echo "worktrees left: $(( $(git worktree list | wc -l) - 1 ))"
echo "agent branches left: $(git branch --list 'worktree-*' '*agent*' 'swarm/*' | wc -l)"
EOF
chmod +x check.sh
printf 'out/\n__pycache__/\n' > .gitignore
sha256sum rt/types.py rt/vec.py rt/png.py render.py scene.json SPEC.md assets/gem.obj tests/*.py tests/data/* > .protected.sha256
git add -A
git commit -qm "Initial import"
