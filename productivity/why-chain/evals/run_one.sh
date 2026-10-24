#!/bin/bash
# Usage: run_one.sh <scenario> <arm: skill|base> <rep>
# Runs one two-turn headless session in a fresh copy of the scenario fixture.
set -u
E=${EVAL_DIR:-$(cd "$(dirname "$0")" && pwd)}
P=$(cd "$(dirname "$0")/.." && pwd)
s=$1; arm=$2; rep=$3
D=$E/runs/${s}_${arm}_${rep}
rm -rf "$D"; mkdir -p "$D"
cp -R "$E/scenarios/$s/fixture" "$D/repo"
cd "$D/repo" || exit 1
git init -q && git add -A && git -c user.name=dev -c user.email=dev@example.com commit -qm "initial" && git rev-parse HEAD > "$D/base_sha"

ALLOW='Read,Grep,Glob,Edit,Write,Bash(git:*),Bash(python3:*),Bash(pytest:*),Bash(cd:*),Bash(ls:*),Bash(cat:*),Bash(wc:*),Bash(time:*),Bash(head:*),Bash(tail:*),Bash(grep:*),Bash(find:*),Bash(echo:*),Bash(printf:*),Bash(awk:*),Bash(sed:*),Bash(sort:*),Bash(uniq:*),Bash(diff:*),Bash(mkdir:*),Bash(touch:*),Bash(cp:*),Bash(mv:*),Bash(for:*),Bash(seq:*),Bash(xargs:*),Bash(tr:*),Bash(cut:*),Bash(true:*),Bash(sleep:*),Bash(env:*)'
DENY='Bash(pip:*),Bash(pip3:*),Bash(python3 -m pip:*),Bash(crontab:*),Bash(launchctl:*),Bash(brew:*),Bash(curl:*),Bash(wget:*),Bash(git push:*),WebFetch,WebSearch'
FLAGS=(--output-format stream-json --verbose --permission-mode dontAsk --allowedTools "$ALLOW" --disallowedTools "$DENY")
[ "$arm" = skill ] && FLAGS+=(--plugin-dir "$P")

req=$(cat "$E/scenarios/$s/request.txt")
[ "$arm" = skill ] && req="/why-chain $req"

start=$(date +%s)
printf '%s' "$req" | claude -p "${FLAGS[@]}" > "$D/turn1.jsonl" 2> "$D/turn1.err"
t1=$(date +%s)
# repo state after turn 1: did it change anything before the user replied?
{ echo "commits_after_initial=$(git rev-list --count HEAD) "; git status --porcelain --untracked-files=all | grep -v -E '__pycache__|\.pytest_cache' ; } > "$D/after_turn1.txt"

sid=$(python3 -c 'import json,sys; print([json.loads(l) for l in open(sys.argv[1]) if l.strip()][-1]["session_id"])' "$D/turn1.jsonl" 2>/dev/null)
if [ -n "$sid" ]; then
  cat "$E/scenarios/$s/followup.txt" | claude -p --resume "$sid" "${FLAGS[@]}" > "$D/turn2.jsonl" 2> "$D/turn2.err"
fi
end=$(date +%s)
echo "{\"turn1_s\": $((t1-start)), \"total_s\": $((end-start))}" > "$D/wall.json"
cd "$D" && diff -ruN --exclude=.git --exclude=__pycache__ --exclude=.pytest_cache "$E/scenarios/$s/fixture" repo > "$D/final.diff"
echo "done $s $arm $rep"
