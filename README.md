# skills

Claude Code skills for personal use, grouped by type. Each skill lives at `<category>/<skill-name>/SKILL.md`.

## design/

| Skill | Description |
|---|---|
| **chart-viz** | Redesign, critique, or build charts as a decision framework — resolves chart type, color, decluttering, and emphasis against the question, data shape, medium, and audience rather than a fixed checklist. |
| **dashboard-design** | Apply expert dashboard design principles when building, auditing, or critiquing dashboards and data tables — enforces data-driven form, progressive disclosure, and invisible UI. |
| **design-loop** | Manual-only `/design-loop`. Interviews for a goal and a real-world reference, tears the reference into checkable mechanisms in `bar.md`, then loops a builder against three fresh-context critics (brief, system, craft) per piece until all three pass. Works at any size, from a whole build down to one component. |
| **extract-dna** | Manual-only `/extract-dna`. Forensically measures one design system — image, URL, PDF, video, code, or design file, one sample or up to six of the same system — into a `dna.json` record plus a `dna.md` guide (capped paste-in payload, nuances, do/don't), proving completeness by rebuilding the reference and diffing it numerically. |
| **mobile-screen-design** | Manual-only `/mobile-screen-design`. Two-pass review or build of a mobile app screen: a defect pass (overlay contrast, media style-consistency, icon axes, mutable state in copy, decision order, action grouping) then a flow pass (scroll context, sticky actions, presets). Each rule is graded by evidence strength, with sources and a debunked-figures list. |
| **tufte-clarity** | Apply Tufte's information design principles to UI layouts, web pages, and presentation slides — reduces chrome, improves signal density. |
| **tufte-viz** | Ideate and critique data visualizations using Tufte's principles: data-ink ratio, chartjunk elimination, graphical integrity, and small multiples. |

## productivity/

| Skill | Description |
|---|---|
| **pdf-to-md** | Convert a PDF, a page range, or one section of it to markdown that keeps the merged-cell tables intact, then verify against the source that no text was lost. |
| **plan-interview** | Walk through a space of interconnected decisions via structured interview — useful when the path forward is unclear and you need to resolve trade-offs before acting. |
| **plan-relax** | Think through a fuzzy or interconnected decision via a relaxed, low-pressure interview — one easy question at a time, ending in a decision summary with defaults filled in. |
| **to-prd** | Turn the current conversation context into a PRD grounded in existing decision logs, without re-interviewing the user. |

## internal-tools/

| Skill | Description |
|---|---|
| **bump-homebrew** | Automate releasing a new Homebrew formula version — tags the repo, builds a deterministic tarball, uploads a GitHub Release asset, and updates the formula. |
| **worktree-swarm** | Split a multi-part fix/feature into worktree-isolated subagents run in parallel, then manually integrate and verify the results. |

## Installing

These are packaged as plugins via the `local-skills` marketplace (`.claude-plugin/marketplace.json`):

```bash
claude plugin marketplace add pathanin/skills
claude plugin install <skill-name>@local-skills
```

Install by skill name — the category directory is repo organization only and is not part of the plugin name.

To pull later updates:

```bash
claude plugin marketplace update local-skills
claude plugin update <skill-name>@local-skills
```

## Moved out

- **jpeg-concat** — now its own repo: https://github.com/pathanin/jpegconcat
