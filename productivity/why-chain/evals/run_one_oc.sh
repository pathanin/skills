#!/bin/bash
# Usage: run_one_oc.sh <scenario> <arm: skill|base> <rep>
# Like run_one.sh, but the builder is opencode (OC_MODEL, default deepseek flash) instead of claude.
# Each run gets a private opencode server and a throwaway HOME, so the user's global
# opencode config, ~/.claude/CLAUDE.md and installed skills don't leak into the builder.
# opencode can't load the plugin, so the skill arm gets SKILL.md injected ahead of the request,
# the way /why-chain expands it in claude. There is no Bash sandbox here: keep EVAL_DIR in a scratch folder.
set -u
E=${EVAL_DIR:-$(cd "$(dirname "$0")" && pwd)}
P=$(cd "$(dirname "$0")/.." && pwd)
MODEL=${OC_MODEL:-opencode/deepseek-v4.1-flash-free}
s=$1; arm=$2; rep=$3
D=$E/runs/${s}_${arm}_ds_${rep}
rm -rf "$D"; mkdir -p "$D/home"
cp -R "$E/scenarios/$s/fixture" "$D/repo"
cd "$D/repo" || exit 1
git init -q && git add -A && git -c user.name=dev -c user.email=dev@example.com commit -qm "initial" && git rev-parse HEAD > "$D/base_sha"

req=$(cat "$E/scenarios/$s/request.txt")
if [ "$arm" = skill ]; then
  body=$(awk 'f>=2; /^---$/{f++}' "$P/SKILL.md")
  req=$(printf '<skill name="why-chain">\n%s\n</skill>\n\nARGUMENTS: %s' "$body" "$req")
fi
oc() { HOME="$D/home" XDG_CONFIG_HOME="$D/home/.config" OPENCODE_DISABLE_CLAUDE_CODE=1 \
  opencode run --standalone --auto --format json -m "$MODEL" "$@" < /dev/null; }

start=$(date +%s)
oc "$req" > "$D/turn1.jsonl" 2> "$D/turn1.err"
t1=$(date +%s)
{ echo "commits_after_initial=$(git rev-list --count HEAD) "; git status --porcelain --untracked-files=all | grep -v -E '__pycache__|\.pytest_cache' ; } > "$D/after_turn1.txt"

sid=$(jq -r 'select(.sessionID) | .sessionID' "$D/turn1.jsonl" 2>/dev/null | head -1)
if [ -n "$sid" ]; then
  oc --session "$sid" "$(cat "$E/scenarios/$s/followup.txt")" > "$D/turn2.jsonl" 2> "$D/turn2.err"
fi
end=$(date +%s)
echo "{\"turn1_s\": $((t1-start)), \"total_s\": $((end-start))}" > "$D/wall.json"
cd "$D" && diff -ruN --exclude=.git --exclude=__pycache__ --exclude=.pytest_cache "$E/scenarios/$s/fixture" repo > "$D/final.diff"
echo "done $s $arm ds $rep"
