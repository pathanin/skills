---
name: claude-graph
description: >
  Manual-only, invoked with /claude-graph. `init` sets up a lean CLAUDE.md plus an
  on-demand .claude/graph.md repo map — where modules, key symbols, and new code go —
  and installs a per-repo staleness check. Bare /claude-graph refreshes both.
  `remove` tears all of it out of the repo. Never fires on its own; ignore this skill
  unless the user typed /claude-graph.
disable-model-invocation: true
---

# claude-graph

## Commands

| Invocation | Do this |
|---|---|
| `/claude-graph init` | Set up both files and the staleness check. Refuse and route to bare `/claude-graph` if `.claude/graph.md` already exists. |
| `/claude-graph` | Refresh an existing graph and re-audit CLAUDE.md. If there is no graph, say so and stop — do not silently init. |
| `/claude-graph remove` | Delete this skill's artifacts from the repo. |

Nothing here runs unprompted. Do not act on this skill because a CLAUDE.md looks bloated or a graph looks stale — only when the user typed the command.

## What this produces

Two files, because two different problems are being solved:

| File | Answers | Loaded | Budget |
|---|---|---|---|
| `CLAUDE.md` | "What would I get **wrong** here?" | Every session, always | ≤ 60 lines |
| `.claude/graph.md` | "**Where** is X?" | On demand, when searching | One line per module, no cap |

Bloated CLAUDE.md files are usually not full of *worthless* content — they are full of navigational content sitting in an always-loaded file. Move it, don't just delete it.

## The split rule

Run every candidate line through this. It is the whole skill.

1. **Would a competent Claude do the wrong thing without it?** → `CLAUDE.md`. Conventions that contradict the obvious default, forbidden moves, non-obvious constraints, the exact verify/build/test command.
2. **Does it only save search time?** → `.claude/graph.md`. File locations, module responsibilities, symbol names, entry points, "where do I add X."
3. **Neither** → delete. Restating general good practice, describing what the code plainly says, aspirational prose, anything already in the user's global `~/.claude/CLAUDE.md` or a parent-directory CLAUDE.md.

Rule 3's last clause does the most work. Read the global and parent CLAUDE.md files **first** and cut everything the project file duplicates.

---

## `/claude-graph init`

### 1. Inventory before writing

Read `~/.claude/CLAUDE.md`, any parent-directory CLAUDE.md, and the existing project `CLAUDE.md`. Classify every line of the project file into the three buckets above before changing anything. Confirm the working tree is clean or the user accepts edits.

### 2. Build the graph

**Run the generator. Do not hand-write the symbol lists.**

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/build_graph.py" . > /tmp/graph.skeleton.md
```

It walks `git ls-files`, extracts every top-level symbol per module, and emits the table with `TODO` in the columns that need judgment. Your job is only to replace those TODOs: `Owns`, `Depends on`, the entry-point descriptions, and the routing list.

Extraction lives in `scripts/lib_symbols.py` and works in two layers: patterns for specific languages, plus a **generic layer that matches declaration *shapes*** — a keyword-plus-name, an assignment whose right side is a function, a parenthesised signature before a brace, a type signature, a DDL statement. The generic layer is why an unfamiliar language usually works: measured on 20 languages with no specific rule, per-language patterns alone resolved 26% of declarations, and the generic layer takes that to 96%.

**On a repo too large for one graph, scope it to a subtree.** Pass a subdirectory instead of the repo root:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/build_graph.py" mm > /tmp/graph.skeleton.md
```

Paths inside a scoped graph stay relative to the **repo root**, not the subtree, so `verify_graph.py` still resolves them and a scoped graph does not hard-block the Stop hook. Write one graph per subtree rather than truncating a whole-repo graph — trimming the symbol column is the failure mode this generator exists to prevent.

The generator warns past **3,000 rows / 1.0MB** and names the largest subtrees to scope to, with their file counts. That budget is set just above the entire benchmark corpus (the largest graph that still loads is buzz at 2,504 rows / 898KB). It is a warning, not an error — the graph is still written. Neither gate catches this: on the Linux kernel, coverage saturates and localization *passes* at 88% while the graph is 65,241 rows / 130MB, 145x anything an agent can read.

**Still read stderr, and check the table has rows.** Four failure modes stay silent in the graph itself:

- *Warned:* files defining functions in some extension yielded no symbols — no pattern covers that language, so rows name the right files and locate nothing in them.
- *Warned:* no recognized code extension at all, so the table is empty. `CODE_EXT` in `build_graph.py` is missing the language.
- *Warned:* the graph is past the size budget — scope it to subtrees, as above.
- *Warned:* no tracked code files under the subtree you named — check the path.

**Closing any of these is a change to this skill, not to the target repo — and it needs the skill's source checkout.** `${CLAUDE_PLUGIN_ROOT}` is a snapshot pinned to a commit: edits written there survive the session, pass the suite, and are silently discarded by the next `claude plugin update`. Never edit under it.

With the checkout, working from its root: add the extension and/or a pattern in `scripts/lib_symbols.py`, **add a fixture to `tests/fixtures/` with its expected symbols in `tests/test_symbols.py`**, then run the suite.

**Derive those expected symbols from `tests/ts_oracle.py`, not by reading the fixture.** It diffs extraction against a real tree-sitter AST and today covers `go`, `python`, `rust`, `svelte`. For a language it does not cover, adding a validated query there is the stronger fix — an expectation eyeballed off the fixture lets the extractor define its own target, the failure `bench_repo.py` exists to prevent.

```bash
python3 tests/test_symbols.py       # after any extraction change
python3 tests/test_scope.py         # after any scoping, size-budget, or Structure change
python3 tests/test_verify.py        # after any staleness-check change
python3 tests/bench_repo.py <repo|url>...   # coverage, against real repos
python3 tests/bench_locate.py <repo|url>... # localization, same repos
```

Green suite is not a working install — and `claude plugin update` does not fix the session you are in. Installs are per-SHA sibling directories, so `${CLAUDE_PLUGIN_ROOT}` keeps resolving to the pre-fix snapshot until a restart. Regenerate with the checkout's generator, never the installed one:

```bash
python3 <checkout>/scripts/build_graph.py <target-repo> > /tmp/graph.skeleton.md
```

Then commit and ship it — `claude plugin marketplace update <marketplace>`, then `claude plugin update claude-graph@<marketplace>`. That is what makes later sessions right; it does nothing for this one.

Without the checkout: name the uncovered language, finish the graph without it, and stop.

**Never hand-write symbols into the graph, in either case.** The next repo in that language would start from scratch, and the hand-patch vanishes on the next refresh.

`test_symbols.py` gates recall across 22 languages and pins the false positives that have actually occurred: a PowerShell verb stranded from its noun, a name truncated at a shell interpolation, a Go package name, a Lua data table read as declarations, control-flow keywords matching the C function shape, `$`-prefixed names. It pins the near-misses beside them, since a name that merely *looks* like a fragment — shell's `stop() {`, Go's `func (w *OSWatcher) Start(` — is a real declaration and was lost to an earlier blocklist.

`bench_repo.py` takes local paths or GitHub URLs (cloning as needed) and reports coverage, graph size, and runtime per repo, failing under 98%. Its expectations are written independently of `lib_symbols.py` on purpose — the extractor must not define its own target.

**Coverage saturates; read it with the other two signals.** Once a language is supported every repo scores 100%, so coverage stops discriminating and starts hiding things.

- *Graph size against repo size.* A 9,000-file repo produced a 6,793-line graph, 91% of whose rows were per-test-case fixture directories, while still scoring 100% — complete, and useless to read. When a graph looks disproportionate, check what the rows actually are before trusting the number.
- *Localization*, via `bench_locate.py`. Coverage is a bag-of-words check over the whole document: it scores a name as found whether the row narrows it to one file or to sixty. That difference is the entire value of the graph, so this harness measures the grep the reader is left holding, and fails under 70% of symbols pinned to a single file. It is what caught the row-splitting policy admitting 12-file directory rows.

A language the benchmark has no patterns for is invisible to both. A Flutter monorepo scored 100% while 237 Dart files were read at 69.5% — when a repo's main language is missing from the `PATS` table in either harness, add it there before believing the score.

**The symbol column must stay exhaustive.** Trimming it to the handful that seem important is the single failure mode that makes a graph worthless — benchmarked across four repos, curated lists resolved 0–50% of symbol lookups while generated ones resolved 100%, at identical always-loaded cost. A symbol you judged unimportant is exactly the one an agent greps for.

The generator handles scale on its own up to a point, and these behaviors matter on a large repo:

- **Dense directories split into one row per file.** Keep the split; don't re-merge it and cut names to fit.
- **Data and asset directories collapse to a single unenumerated row** (`754 data/asset files, not enumerated`). Test directories never collapse — the routing table has to name where a test goes.
- **Past the size budget, scope to subtrees** rather than letting one graph grow unreadable. Row splitting is what makes a graph locate; it is also what makes it large, and the two stop being reconcilable somewhere above the corpus. The kernel needs roughly one graph per subsystem — `mm` lands at 193 rows, `kernel` at 640, while `drivers/net` alone still wants splitting further.

Do not reintroduce a per-file symbol cap. An earlier version capped at 25 and silently dropped 185 symbols on a 1,896-file repo, every one in a file the graph already named — the row looked complete while still sending the agent to grep.

Then write `.claude/graph.md`, using this shape:

```markdown
<!-- generated: 2026-07-26 @ <short-sha> — when this disagrees with the repo, the repo wins: fix the row. -->

## Structure
<!-- Mechanical rollup of the table below; regenerated wholesale. -->
- `internal/` — 445 code files in 38 dirs · `.go`
- `client/` — 225 code files in 53 dirs · `.tsx`, `.ts`, `.js`
- (repo root) — 3 code files · `.go`, `.js`

## Entry points
- `cmd/server/main.go` — process boot; wires config → handlers → store.

## Modules
| Path | Owns | Key symbols | Depends on |
|---|---|---|---|
| `internal/auth/` | session issue + verify | `NewSession`, `Verify`, `Middleware` | `internal/store`, `pkg/jwt` |

## Where do I add X?
- New HTTP endpoint → route in `internal/api/routes.go`, handler in `internal/api/handlers/`
- New migration → `migrations/`, sequential numeric prefix
```

**`## Structure` is generated, not written, and appears only past 40 module rows.** It is orientation, not navigation: one line per subtree at scope depth + 1, with counts and extensions. Below the gate the table is already the overview and the rollup would restate the Path column, so the generator emits nothing — leave it out rather than hand-writing one.

Measured across gin, croc, fastapi, copyparty, AdGuardHome and svelte, it costs 0.15–0.91% of graph bytes and moves no quality metric: reach, 1-file localization, mean/p90 grep size, misattribution, coverage and dir-coverage are all identical with and without it.

Two rules keep it that way, and both are load-bearing:

- **Never a table.** A `|` line whose first cell is a backticked path is read as a *module row* by `verify_graph.parse_graph`, `bench_locate.parse_rows` and `bench_repo.modules_only`. A rollup line places no symbol, so admitting it to any of those corrupts the measurement.
- **Never a substitute for a row.** Its paths are checked for rot like any other, but they do not count as coverage — a `binding/` line stands in for every directory beneath it. Counting them took the SessionStart unmapped-dirs advisory from 3 flagged directories to 0 on gin and 8 to 0 on croc: inert while looking guarded.

Hard rules for the graph:

- **Paths and symbol names only — never line numbers, never copied code.** Line numbers rot on the next commit; a pointer index stays valid far longer.
- **Every public symbol the generator found stays in.** Delete a row only if the whole module is vendored or generated.
- One row per directory an agent would plausibly search in; per-file rows where the generator split a dense directory.
- "Owns" is one clause about responsibility, not a summary of the files.
- No behavioral advice. If a line tells someone what *not* to do, it belongs in CLAUDE.md.

**Before moving on, check nothing was lost.** Every file path and symbol the old CLAUDE.md named must appear somewhere in the new pair. Demoting navigation to the graph is a move, not a deletion — a benchmark run caught the first version of this skill silently dropping 11 symbols the original CLAUDE.md had named.

Also confirm every path resolves. On a large repo the old CLAUDE.md may name paths that no longer exist; the staleness check will block on them at the end of the turn, so fix them now rather than carrying the error into the graph.

### 3. Write the lean CLAUDE.md

In this order, and only what applies:

1. One or two sentences on what the project is — enough to disambiguate, not an overview.
2. **The pointer line, mandatory** — verbatim:

   ```markdown
   Before searching for a file or symbol, read `.claude/graph.md` — it maps modules, key symbols, and where to add new code.
   ```

   Use a plain path, **not** `@.claude/graph.md`; the `@` form inlines the file into every session and destroys the reason for splitting.
3. Conventions that contradict what Claude would otherwise assume.
4. The exact commands to build, test, and verify — copy-pasteable, with the one thing that breaks if run wrong.
5. Known traps: things that look safe and aren't.

Cut on sight: directory trees (the graph has them), inventories of every npm script, framework explanations, "write clean code" guidance, and anything hedged enough that it changes no decision.

### 4. Install the staleness check

Copy this skill's checker into the target repo — the repo owns its copy, so teammates without this plugin still get the check. **Copy both files, not just the first:**

```bash
mkdir -p .claude/claude-graph
cp "${CLAUDE_PLUGIN_ROOT}/scripts/verify_graph.py" .claude/claude-graph/verify_graph.py
cp "${CLAUDE_PLUGIN_ROOT}/scripts/lib_extensions.py" .claude/claude-graph/lib_extensions.py
```

`verify_graph.py` does `from lib_extensions import CODE_EXT, SKIP_PARTS` against its own directory. Copying it alone makes both hooks die with `ModuleNotFoundError` — and since a crashed `Stop` hook blocks nothing, the repo looks guarded while the check is inert. `lib_extensions.py` imports nothing further, so these two are the whole dependency.

Then confirm it actually runs, rather than assuming it did:

```bash
echo '{}' | CLAUDE_PROJECT_DIR="$PWD" python3 .claude/claude-graph/verify_graph.py Stop
```

Silence is a pass; a traceback means the copy is incomplete. A JSON `"decision": "block"` payload means the graph has dead rows — fix those rows before finishing.

Then merge into the repo's `.claude/settings.json`, preserving any hooks already there:

```json
{
  "hooks": {
    "Stop": [{"matcher": "", "hooks": [{"type": "command",
      "command": "python3 \"$CLAUDE_PROJECT_DIR/.claude/claude-graph/verify_graph.py\" Stop"}]}],
    "SessionStart": [{"matcher": "", "hooks": [{"type": "command",
      "command": "python3 \"$CLAUDE_PROJECT_DIR/.claude/claude-graph/verify_graph.py\" SessionStart"}]}]
  }
}
```

Check whether `.claude/` is gitignored; if it is, tell the user the graph and hook won't reach teammates until that changes. Finally, tell the user the check is now active in this repo only, and that dropping the `Stop` entry leaves it advisory-only.

---

## `/claude-graph` (no argument) — refresh

**Re-copy the checker first.** The repo owns its copy of `verify_graph.py`, so a refresh that only rewrites the graph leaves an old checker reading a new format:

```bash
cp "${CLAUDE_PLUGIN_ROOT}/scripts/verify_graph.py" .claude/claude-graph/verify_graph.py
cp "${CLAUDE_PLUGIN_ROOT}/scripts/lib_extensions.py" .claude/claude-graph/lib_extensions.py
```

Measured on gin: the current generator emits `## Structure`, a checker predating it counts those paths as coverage, and the SessionStart advisory drops from 3 flagged directories to nothing. It does not crash — the old file is self-consistent — so the repo looks guarded while the check is inert, the same failure as copying `verify_graph.py` without `lib_extensions.py`. The graph format and the checker that reads it version together; refresh moves both.

Then re-run `build_graph.py` and merge: take the regenerated symbol columns **and the whole `## Structure` section** wholesale, and carry the existing `Owns`, `Depends on`, and "Where do I add X?" text across unchanged unless the code it describes moved. The mechanical parts are the generator's; the judgment parts are the repo's. `## Structure` holds no judgment — replace it outright rather than merging it, and let it disappear if the repo has dropped back under the gate. Update the generated-at comment and report what changed.

## `/claude-graph remove`

List the targets first, then delete only what exists, then confirm with the user before touching anything:

1. `.claude/graph.md`
2. `.claude/claude-graph/verify_graph.py` (and the directory, if now empty)
3. The two hook entries in `.claude/settings.json` — remove **only** those two commands; leave every other hook and setting intact, and drop the `hooks` key entirely only if it ends up empty.
4. The pointer line in `CLAUDE.md`.

Leave the rest of `CLAUDE.md` alone — after `init` it is the user's project guidance, not this skill's artifact. Say so, and say that the plugin itself stays installed.

## How the staleness check behaves

| Event | Detects | Effect |
|---|---|---|
| `Stop` (end of turn) | A path named in the graph no longer exists; a symbol in a Key-symbols cell is gone from its module | **Blocks** — fix the affected rows before finishing |
| `SessionStart` | The above, plus code directories with no row | Advisory note only |

It deliberately does **not** flag new symbols in a mapped module — "Key symbols" is a curated selection, not an inventory, so treating additions as drift would nag on every edit. Only the two failures that actively mislead an agent block.

When it fires, repair the named rows and nothing else, then refresh the generated-at comment. A dead path it names may sit in `## Structure` rather than in a row — that section is generated, so regenerate it instead of editing the line. Full regeneration is `/claude-graph`, for when directories are added or removed wholesale.

Escape hatch: a line containing `<!-- claude-graph: no-verify -->` anywhere in the graph disables the check for that repo. Use it during an intentional migration; remove it after.

## Versus the built-in `/init`

`/init` writes one always-loaded file containing architecture summaries, directory trees, and command inventories — the exact payload that makes CLAUDE.md too expensive to keep and too long to obey. This skill keeps that content but demotes it to an on-demand file, leaving CLAUDE.md as behavior only. Use `/init` when the user explicitly wants the standard single-file output.

## Report back

State: lines before → after for CLAUDE.md, what moved to the graph, what was deleted as redundant with the global or parent file, and which modules the graph covers. If something was ambiguous between buckets, name it rather than silently placing it.
