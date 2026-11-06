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
| [chart&#8209;viz](design/chart-viz/SKILL.md) | `/chart-viz` | Picks chart type, color, decluttering and emphasis from the question, data, medium and audience. |
| [code&#8209;animation](design/code-animation/SKILL.md) | `/code-animation` | Code-built animation rendered frame-exact in headless Chromium; exports MP4, GIF, WebM, ProRes with alpha. |
| [code&#8209;wallpaper](design/code-wallpaper/SKILL.md) | `/code-wallpaper` | Code-painted landscape wallpaper, oil on linen or layered paper cut, PNG at any resolution. |
| [critic&#8209;loop](design/critic-loop/SKILL.md) | `/critic-loop` | Builder revises against fresh-context critics until none blocks and all clear a score floor. No reference needed. |
| [dashboard&#8209;design](design/dashboard-design/SKILL.md) | auto | Dashboard and data-table principles: data-driven form, progressive disclosure, invisible UI. |
| [design&#8209;loop](design/design-loop/SKILL.md) | `/design-loop` | Breaks a real-world reference into checkable mechanisms, then loops builder vs. three critics per piece. |
| [extract&#8209;dna](design/extract-dna/SKILL.md) | `/extract-dna` | Measures a design system into `dna.json` + `dna.md`, proven by rebuilding and diffing the reference. |
| [interaction&#8209;intent](design/interaction-intent/SKILL.md) | `/interaction-intent` | What an ambiguous click, tap or drag meant, and how actions commit and undo. Confirmations only when irreversible. |
| [mobile&#8209;screen&#8209;design](design/mobile-screen-design/SKILL.md) | `/mobile-screen-design` | Two-pass review or build of a mobile screen (defects, then flow), rules graded by evidence. |
| [ui&#8209;style](design/ui-style/SKILL.md) | `/ui-style` | My preferred UI look: flat, neutral grays, hairline borders, tints instead of shadows. |
| [tufte&#8209;clarity](design/tufte-clarity/SKILL.md) | auto | Tufte's principles for UI, web pages and slides: less chrome, more signal. |
| [tufte&#8209;viz](design/tufte-viz/SKILL.md) | auto | Tufte's principles for charts: data-ink, no chartjunk, graphical integrity, small multiples. |
| [wallpaper&#8209;upscale](design/wallpaper-upscale/SKILL.md) | `/wallpaper-upscale` | Image, thumbnail or video frame to high-res Mac wallpaper, upscaled locally on the Apple GPU. |

## productivity

| Skill | Run | What it does |
|---|---|---|
| [html&#8209;presentation](productivity/html-presentation/SKILL.md) | `/html-presentation` | Deck as HTML from a .pptx or from scratch; in-browser edits and comment pins; exports editable PPTX with animations, or PDF. |
| [kickoff](productivity/kickoff/SKILL.md) | `/kickoff` | Vague idea to a short `BRIEF.md`, asking only the Why/Who/What/Which/Whether/When gaps that change the build. |
| [pdf&#8209;to&#8209;md](productivity/pdf-to-md/SKILL.md) | auto | PDF (or a range or section) to markdown with merged-cell tables intact, checked against the source. |
| [plain&#8209;writing](productivity/plain-writing/SKILL.md) | `/plain-writing` | Plain prose style; `deslopify` rewrites the last reply. Vendored from [docwriter-org/plain-writing-skill](https://github.com/docwriter-org/plain-writing-skill) (MIT). |
| [plan&#8209;interview](productivity/plan-interview/SKILL.md) | auto | Structured interview through interconnected decisions before acting. |
| [plan&#8209;relax](productivity/plan-relax/SKILL.md) | auto | Low-pressure, one-question-at-a-time decision interview ending in a summary with defaults. |
| [to&#8209;prd](productivity/to-prd/SKILL.md) | auto | Turns the current conversation into a PRD grounded in existing decision logs. |
| [translate&#8209;to&#8209;thai](productivity/translate-to-thai/SKILL.md) | auto | Natural Thai translation that keeps technical terms and product names in English. |
| [why&#8209;chain](productivity/why-chain/SKILL.md) | `/why-chain` | Asks why until it reaches the root cause behind a request, rebuilds the fix from there, and tests the root before building. |

## internal-tools

| Skill | Run | What it does |
|---|---|---|
| [build&#8209;fast](internal-tools/build-fast/SKILL.md) | `/build-fast` | Fastest working first-draft script on the real input; scaffolding cut, correctness kept. |
| [bump&#8209;homebrew](internal-tools/bump-homebrew/SKILL.md) | auto | Releases a Homebrew formula version: tag, deterministic tarball, GitHub Release, formula update. |
| [fresh&#8209;start](internal-tools/fresh-start/SKILL.md) | `/fresh-start` | Rewrites from the old code's behavior contract, diffs both, keeps the simpler correct one. |
| [searx&#8209;search](internal-tools/searx-search/SKILL.md) | auto | Backup web search through a local SearXNG when WebSearch is blocked. Backup copy; not in the marketplace. |
| [worktree&#8209;swarm](internal-tools/worktree-swarm/SKILL.md) | auto | Splits work across parallel worktree-isolated subagents, then integrates and verifies by hand. |

## mods

Hook plugins that change Claude Code itself. Test with `claude plugin test mods/<name>`.

| Mod | Runs in | What it does |
|---|---|---|
| [clawd](mods/clawd/hooks/register.tsx) | CLI | Clawd on the prompt border: types while Claude works, idles with small animations. `/clawd` toggles him; `/clawd image` draws him as a picture (kitty, Ghostty). |
| [limits](mods/limits/README.md) | App | 5-hour and weekly usage, reset countdowns and context fill above the prompt. From [Ryan-LT/claude-mods](https://github.com/Ryan-LT/claude-mods). |
| [live&#8209;tasks](mods/live-tasks/hooks/register.tsx) | CLI | The app's pinned task list above the prompt, checked off as Claude works. `/live-tasks` shows, hides or clears it. |
| [reply&#8209;quote](mods/reply-quote/hooks/register.tsx) | CLI | `/reply` quotes a paragraph of the last reply, your selection or clipboard into the prompt. Fullscreen: hover a paragraph for ↩. |
