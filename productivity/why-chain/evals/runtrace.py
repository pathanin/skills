"""Condense a stream-json transcript into a readable trace, and pull run metrics.

Usage: python3 trace.py <turn.jsonl>            -> prints the trace
       python3 trace.py --metrics <turn.jsonl>  -> prints a JSON metrics object
"""
import json
import sys

CLIP = 1200


def clip(s, n=CLIP):
    s = s if isinstance(s, str) else json.dumps(s)
    return s if len(s) <= n else s[:n] + f" …[{len(s) - n} more chars]"


def events(path):
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    pass


def trace(path):
    out = []
    for ev in events(path):
        t = ev.get("type")
        if t == "assistant":
            for block in ev["message"].get("content", []):
                if block.get("type") == "text" and block["text"].strip():
                    out.append(f"[assistant]\n{block['text'].strip()}")
                elif block.get("type") == "tool_use":
                    out.append(f"[tool call: {block['name']}] {clip(block.get('input'), 600)}")
        elif t == "user":
            content = ev["message"].get("content", [])
            if isinstance(content, list):
                for block in content:
                    if block.get("type") == "tool_result":
                        c = block.get("content")
                        if isinstance(c, list):
                            c = "\n".join(x.get("text", "") for x in c if isinstance(x, dict))
                        out.append(f"[tool result] {clip(c)}")
    return "\n\n".join(out)


def metrics(path):
    res = {}
    for ev in events(path):
        if ev.get("type") == "result":
            res = ev
    return {
        "cost_usd": res.get("total_cost_usd"),
        "num_turns": res.get("num_turns"),
        "duration_ms": res.get("duration_ms"),
        "denials": len(res.get("permission_denials") or []),
        "is_error": res.get("is_error"),
        "final_text": res.get("result", ""),
    }


if __name__ == "__main__":
    if sys.argv[1] == "--metrics":
        print(json.dumps(metrics(sys.argv[2])))
    else:
        print(trace(sys.argv[1]))
