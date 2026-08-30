# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A personal collection of Claude Code **Skills** — no application code, no build/test/lint pipeline. Skills are grouped into three category directories: `design/`, `productivity/`, and `internal-tools/`. Each directory *inside* a category is one skill: a `SKILL.md` (instructions loaded into context when the skill triggers) plus, optionally, `scripts/`, `assets/`, and `references/` subdirectories the skill's instructions point to.

Categories are organizational only — plugin identity is the leaf directory name, which must match `name:` in both `SKILL.md` and `.claude-plugin/plugin.json`. Moving a skill between categories requires updating its `source` in `.claude-plugin/marketplace.json` to `./<category>/<skill>` (nested paths resolve fine), then commit + `claude plugin marketplace update local-skills` + `claude plugin update <name>@local-skills`.

See `README.md` for the current skill list and one-line descriptions — keep that table in sync when adding, renaming, moving, or removing a skill.

## Skill anatomy

Every `SKILL.md` starts with YAML frontmatter:

```yaml
---
name: skill-name          # matches the directory name
description: >            # the ONLY signal Claude uses to decide when to trigger this skill
  ...
---
```

The `description` is load-bearing: it's matched against the user's request to decide whether the skill fires at all, so it must state concrete trigger phrases *and* explicit skip conditions (see any existing `SKILL.md` for the pattern — e.g. `bump-homebrew`'s description lists both trigger phrasings and what to skip). When editing a skill, prefer tightening `description` over adding disclaimers in the body.

Supporting subdirectories, used inconsistently by design (each skill only has what it needs):
- `scripts/` — standalone Python invoked via `bash`/`python3` from the skill body. These are stdlib-only or declare their deps in prose inside `SKILL.md`, not in a `requirements.txt`.
- `assets/` — template files a script copies/edits rather than generates from scratch.
- `references/` — longer reference docs the skill body explicitly tells Claude to load only when needed, to avoid bloating the always-loaded `SKILL.md` (e.g. `design/tufte-viz/references/*.md`, `design/tufte-clarity/references/clarity-principles.md`).
- `.claude-plugin/plugin.json` — plugin manifest, present only on skills packaged as plugins; not a repo-wide convention.

## Working on a skill

- Treat `SKILL.md` as a prompt, not documentation — every sentence is an instruction to a future Claude instance, not an explanation for a human reader. Write imperatively, resolve ambiguity explicitly (numbered steps, exact command blocks, explicit stop/ask conditions), and avoid narrative filler.
- Several skills are process/interview skills with no code at all (`plan-relax`, `to-prd`, `dashboard-design`, `tufte-clarity`, `tufte-viz`). Changes to these are pure prompt-engineering: reread the whole file for internal consistency (numbered workflows, "when to stop/ask" rules, output contracts) rather than editing a section in isolation.
- `plan-relax` is deliberately low-pressure and hides progress from the user. Keep that tone when editing it — don't make it brisk or numbered, and don't add progress indicators or question counts.
- `tufte-clarity` and `tufte-viz` are siblings: `tufte-viz` is for actual data visualizations/charts, `tufte-clarity` generalizes the same principles to UI/web/slide design and explicitly cross-references `tufte-viz` for the data-viz-specific case. Keep the "Core Translation" table in `design/tufte-clarity/SKILL.md` in sync if Tufte concepts are added to `tufte-viz`.

## No build/lint/test commands

There is nothing to compile, lint, or test — skills are prompts, not code. Verify changes by reading the `SKILL.md` end to end for internal consistency.
