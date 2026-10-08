---
type: tool_used
tool: Agent
input_match: '^(?!.*"isolation")(?=.*"model":"opus")(?=.*"effort":"low")(?=.*diff)(?=.*PASS)(?=.*FAIL)(?=.*(?:(?:NOT|[Nn]ot|n.t) (?:edit|commit|modify)|[Rr]ead-only|[Rr]ead only))(?=.*unittest)(?!.*agent-([0-9a-f]{8,}).*agent-(?!\1)[0-9a-f]{8,})'
min: 2
arm: both
---
