#!/bin/bash
# Run one eval case as a fresh `claude -p` session with this plugin loaded, without the eval harness's sandbox.
# For containers where `claude plugin eval` cannot sandbox Bash (see README.md). The container itself is the isolation.
# usage: evals/run-local.sh <case> [out-dir]      then: python3 evals/grade-local.py <case> [out-dir]
set -e
C=$1; HERE=$(cd "$(dirname "$0")" && pwd); PLUGIN=$(dirname "$HERE"); W=${2:-${TMPDIR:-/tmp}/code-animation-evals}/$C
[ -f "$HERE/$C/prompt.md" ] || { echo "no case $C"; exit 1; }
rm -rf "$W"; mkdir -p "$W/work"; cd "$W/work"; bash "$HERE/$C/fixture.sh"
PROMPT=$(awk 'BEGIN{n=0} /^---$/{n++; next} n>=2{print}' "$HERE/$C/prompt.md" | sed '/^$/d')
TURNS=$(grep -m1 max_turns "$HERE/$C/prompt.md" | awk '{print $2}'); SECS=$(grep -m1 timeout_seconds "$HERE/$C/prompt.md" | awk '{print $2}')
timeout "${SECS:-3600}" claude -p "$PROMPT" --plugin-dir "$PLUGIN" --permission-mode dontAsk --allowedTools Read Glob Grep Skill Bash Write Edit \
  --max-turns "${TURNS:-150}" --output-format stream-json --verbose > "$W/trace.jsonl" 2> "$W/stderr.log" || true
echo "trace: $W/trace.jsonl"
