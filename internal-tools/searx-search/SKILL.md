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

Tell the user briefly that the normal search was blocked and you fell back to SearXNG.
