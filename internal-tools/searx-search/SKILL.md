---
name: searx-search
description: Backup web search through the user's local SearXNG instance. Use when WebSearch (or WebFetch on a search page) fails, is blocked, rate-limited, returns a CAPTCHA/bot-check, or comes back empty for a query that should have results. Also use when the user asks to search via SearXNG/searx.
---

# Backup search via local SearXNG

The user runs SearXNG locally at `~/.local/share/searxng` (127.0.0.1 only). The script starts it automatically when needed (a few seconds the first time) and leaves it running; a SessionEnd hook in `~/.claude/settings.json` stops it when the session exits.

```bash
python3 ~/.claude/skills/searx-search/search.py "your query" [-n 10] [--category general|news|it|science] [--json]
```

- Prints numbered results: title, URL, snippet.
- `--json` returns raw results (includes `engines`, `publishedDate` where available).
- To read a result page, use WebFetch on its URL; if that is also blocked, `curl -sL <url>` is fine.
- If it fails, check the end of `~/.local/share/searxng/server.log`. Stop the server with `pkill -f searx.webapp`.

## First-time setup (new machine)

If `~/.local/share/searxng/venv` doesn't exist, set it up once (needs `uv`; takes a minute or two):

```bash
sh ~/.claude/skills/searx-search/setup.sh
```

It downloads SearXNG into `~/.local/share/searxng/src`, builds a Python 3.12 venv with uv and writes `settings.yml` (localhost only, JSON enabled, a fresh random `secret_key`). It's safe to re-run, and an existing `settings.yml` is kept. Then run one test search.

To stop the server when a Claude session ends, add this to `hooks` in `~/.claude/settings.json`. Merge it into an existing `SessionEnd` list if there is one:

```json
"SessionEnd": [
  { "hooks": [ { "type": "command", "command": "pkill -f 'searxng/venv/bin/python -m searx.webapp' || true", "timeout": 5 } ] }
]
```

To install this skill from the repo backup, copy the folder: `cp -R <repo>/internal-tools/searx-search ~/.claude/skills/`.

Tell the user briefly that the normal search was blocked and you fell back to SearXNG.
