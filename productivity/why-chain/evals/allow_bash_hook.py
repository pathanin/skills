"""PreToolUse hook for eval runs: allow any Bash command unless it hits the deny list.

The prefix allowlist refuses loops, heredocs and `VAR=… cmd` forms under dontAsk.
Runs also enable the Bash sandbox, which keeps writes inside the run and blocks network.
"""
import json
import re
import sys

DENY = re.compile(r"(^|[;&|(\s])(pip3?|curl|wget|brew|crontab|launchctl|git\s+push|python3?\s+-m\s+pip)\b")

ev = json.load(sys.stdin)
cmd = ev.get("tool_input", {}).get("command", "")
decision = "deny" if DENY.search(cmd) else "allow"
print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": decision,
                                         "permissionDecisionReason": "eval harness policy"}}))
