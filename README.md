<img src="assets/banner.gif" alt="skills" width="100%">

# skills

Claude Code skills for personal use, grouped by type. Each skill lives at `<category>/<skill-name>/SKILL.md`.

**[design](#design)** · **[productivity](#productivity)** · **[internal-tools](#internal-tools)** · **[mods](#mods)**

## Install

Packaged as plugins in the `local-skills` marketplace (`.claude-plugin/marketplace.json`). Install by skill name; the category folder is not part of the plugin name.

```bash
claude plugin marketplace add pathanin/skills
claude plugin install <skill-name>@local-skills

# later updates
claude plugin marketplace update local-skills
claude plugin update <skill-name>@local-skills
```

**Run** column: `/name` means manual-only, so Claude won't load it on its own and you type the command. `auto` means Claude loads it when the task fits.

## design

| Skill | Run | What it does |
|---|---|---|
| [chart-viz](design/chart-viz/SKILL.md) | `/chart-viz` | Picks chart type, color, decluttering and emphasis from the question, data, medium and audience. |
| [code-animation](design/code-animation/SKILL.md) | `/code-animation` | Code-built animation rendered frame-exact in headless Chromium; exports MP4, GIF, WebM, ProRes with alpha. |
| [code-wallpaper](design/code-wallpaper/SKILL.md) | `/code-wallpaper` | Code-painted landscape wallpaper, oil on linen or layered paper cut, PNG at any resolution. |
| [critic-loop](design/critic-loop/SKILL.md) | `/critic-loop` | Builder revises against fresh-context critics until none blocks and all clear a score floor. No reference needed. |
| [dashboard-design](design/dashboard-design/SKILL.md) | auto | Dashboard and data-table principles: data-driven form, progressive disclosure, invisible UI. |
| [design-loop](design/design-loop/SKILL.md) | `/design-loop` | Breaks a real-world reference into checkable mechanisms, then loops builder vs. three critics per piece. |
| [extract-dna](design/extract-dna/SKILL.md) | `/extract-dna` | Measures a design system into `dna.json` + `dna.md`, proven by rebuilding and diffing the reference. |
| [mobile-screen-design](design/mobile-screen-design/SKILL.md) | `/mobile-screen-design` | Two-pass review or build of a mobile screen (defects, then flow), rules graded by evidence. |
| [tufte-clarity](design/tufte-clarity/SKILL.md) | auto | Tufte's principles for UI, web pages and slides: less chrome, more signal. |
| [tufte-viz](design/tufte-viz/SKILL.md) | auto | Tufte's principles for charts: data-ink, no chartjunk, graphical integrity, small multiples. |
| [wallpaper-upscale](design/wallpaper-upscale/SKILL.md) | `/wallpaper-upscale` | Image, thumbnail or video frame to high-res Mac wallpaper, upscaled locally on the Apple GPU. |

## productivity

| Skill | Run | What it does |
|---|---|---|
| [pdf-to-md](productivity/pdf-to-md/SKILL.md) | auto | PDF (or a range or section) to markdown with merged-cell tables intact, checked against the source. |
| [plain-writing](productivity/plain-writing/SKILL.md) | `/plain-writing` | Plain prose style; `deslopify` rewrites the last reply. Vendored from [docwriter-org/plain-writing-skill](https://github.com/docwriter-org/plain-writing-skill) (MIT). |
| [plan-interview](productivity/plan-interview/SKILL.md) | auto | Structured interview through interconnected decisions before acting. |
| [plan-relax](productivity/plan-relax/SKILL.md) | auto | Low-pressure, one-question-at-a-time decision interview ending in a summary with defaults. |
| [to-prd](productivity/to-prd/SKILL.md) | auto | Turns the current conversation into a PRD grounded in existing decision logs. |
| [translate-to-thai](productivity/translate-to-thai/SKILL.md) | auto | Natural Thai translation that keeps technical terms and product names in English. |

## internal-tools

| Skill | Run | What it does |
|---|---|---|
| [build-fast](internal-tools/build-fast/SKILL.md) | `/build-fast` | Fastest working first-draft script on the real input; scaffolding cut, correctness kept. |
| [bump-homebrew](internal-tools/bump-homebrew/SKILL.md) | auto | Releases a Homebrew formula version: tag, deterministic tarball, GitHub Release, formula update. |
| [fresh-start](internal-tools/fresh-start/SKILL.md) | `/fresh-start` | Rewrites from the old code's behavior contract, diffs both, keeps the simpler correct one. |
| [worktree-swarm](internal-tools/worktree-swarm/SKILL.md) | auto | Splits work across parallel worktree-isolated subagents, then integrates and verifies by hand. |

## mods

Hook plugins that draw inside Claude Code rather than skills. Test with `claude plugin test mods/<name>`.

| Mod | What it does |
|---|---|
| [reply-quote](mods/reply-quote/hooks/register.tsx) | `/reply` quotes a paragraph of Claude's last reply, your selection or clipboard into the prompt; hover ↩ in fullscreen. |
