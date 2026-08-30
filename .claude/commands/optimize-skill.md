---
description: Benchmark claude-graph against repos and fix what breaks
argument-hint: [repo urls or paths...]
allowed-tools: Bash, Read, Edit, Write, Glob, Grep
---

Benchmark the `claude-graph` generator against the repos in `$ARGUMENTS`, fix what breaks, and report. If `$ARGUMENTS` is empty, ask which repos to test and stop.

Skill root: `~/Documents/skills/internal-tools/claude-graph`. Work there; all paths below are relative to it.

## 1. Baseline

Run all three **before** touching anything, so any later failure is attributable:

```bash
python3 tests/test_symbols.py
python3 tests/bench_repo.py $ARGUMENTS      # coverage — expect 100%, it is saturated
python3 tests/bench_locate.py $ARGUMENTS    # localization — this one still discriminates
```

Both benches accept GitHub URLs or local paths and clone as needed. Record the untuned numbers verbatim — they are the honest held-out result, and they stay in the final report even after you fix things.

## 2. Read past the coverage number

Coverage saturates at 100% once a language is supported. Treat it as a smoke test, not a score: it is a bag-of-words check over the whole document, so it scores a name as found whether the row narrows it to one file or to sixty.

Two gates, then four checks no gate covers:

- **Coverage** (`bench_repo.py`) — under 98% fails. Diagnose with `python3 tests/bench_repo.py --misses <repo>`.
- **Localization** (`bench_locate.py`) — under 70% of symbols pinned to a single file fails. This is the metric that still moves; it spread twelve repos across 58–95% and caught a row-splitting policy that left 34% of symbols resolving only to a directory. Diagnose with `--worst <repo>`, which prints the symbols with the largest remaining grep.
- **A language neither harness can see.** Each has its own `PATS` table, and a language absent from it is not scored at all — the repo just looks perfect. A Flutter monorepo scored 100% on coverage while the extractor was reading 69.5% of its 237 Dart files. Before believing any score, check the repo's main languages are in `PATS`:

  ```bash
  git -C <repo> ls-files | sed 's/.*\.//' | sort | uniq -c | sort -rn | head
  ```

- **Graph size against repo size.** A graph disproportionate to the repo means rows that carry nothing. One 9,000-file repo scored 100% while emitting 6,793 lines of which 91% were per-test-case fixture directories. Inspect what the rows actually are: `grep -o '^| \`[^\`]*\`' <graph> | sed 's/| \`//;s/\`//' | cut -d/ -f1-3 | sort | uniq -c | sort -rn | head`.
- **Generator stderr.** A warning about an unrecognized extension or a language yielding no symbols means rows that name the right files and locate nothing.
- **The verifier against the graph just generated.** It caught a stale duplicated extension list and a `\b`-vs-`$` boundary bug, each a false block on every repo in an affected language. Note what it does *not* catch: it only checks a symbol is *present* in the module, which an import or a call satisfies, so a symbol declared in B and listed under A passes here and only fails in `bench_locate.py`'s `misattr` column.

```bash
python3 - <<'PY'
import json, os, subprocess
for root in ["<repo>", ...]:
    g = subprocess.run(['python3','scripts/build_graph.py',root],
                       capture_output=True, text=True).stdout
    d = os.path.join(root,'.claude'); os.makedirs(d, exist_ok=True)
    p = os.path.join(d,'graph.md')
    existed = os.path.exists(p); bak = open(p).read() if existed else None
    open(p,'w').write(g)
    r = subprocess.run(['python3','scripts/verify_graph.py','Stop'],
                       input=json.dumps({"cwd":root}), capture_output=True, text=True)
    print(os.path.basename(root),
          json.loads(r.stdout)["reason"][:120] if r.stdout.strip() else "CLEAN")
    if existed: open(p,'w').write(bak)
    else: os.remove(p)
PY
```

## 3. Diagnose before changing anything

Find the *class* that was missed, not the individual symbol. Read the real source line. `const ErrX errors.Error = "…"` was a class of miss (typed binding, no bare `=`), not one symbol; `final fooProvider =` was 80 of one repo's 165.

Then decide where the defect actually is — three possibilities, and they are not equally likely:

1. **The extractor** (`scripts/lib_symbols.py`) — a grammar it does not cover. This is where a *coverage* miss usually lives.
2. **The generator** (`scripts/build_graph.py`) — extensions, fixture collapsing, and the row-splitting thresholds. This is where a *localization* miss usually lives: a directory row answers "which file?" with "one of these N", so `FILE_ROW_THRESHOLD` and `FILE_COUNT_THRESHOLD` set how much grep the reader is left holding.
3. **A harness's own expectations** (`tests/bench_repo.py`, `tests/bench_locate.py`). Suspect this early — it has been wrong three times: counting symbols inside individual test cases nobody navigates to; having no Dart patterns, so a whole language read as perfect; and counting a directory row's files recursively when `build_graph.py` groups by `os.path.dirname`, which made `(repo root)` look like a 7,927-file search. **A harness bug that inflates a number will drive your fix off a value the generator never produced.** If the "missed" names are things no agent would grep for, or a number looks impossible, fix the harness first and re-measure.

If the language has a decent tree-sitter grammar, don't just eyeball source to settle which of the three it is — run `tests/ts_oracle.py <path-or-url> --lang <language>` (optional dep, `pip install tree-sitter tree-sitter-<language>`; it prints one line and exits 0 if that's not installed). It diffs the regex extraction against a real AST and buckets the disagreement into "regex found, tree-sitter didn't" (a false positive, or the query needs widening) and "tree-sitter found, regex didn't" (a real gap — or check `KEYWORDS` and the 3-char minimum before assuming so). This exact comparison against a 25-repo Rust corpus found three real bugs in one session that no gate above saw: `new`/`delete`/`default`/`from` sitting in `KEYWORDS` as a blanket blocklist, the Vue `name:` heuristic reading Go test tables and Rust data literals as declarations, and `impl Trait for Type` misattributing the trait name as a declaration. `rust`, `python`, and `go` have validated queries so far — see the script's docstring before adding another language's.

## 4. Fix centrally, never per repo

Fix the script so every future repo in that language inherits it. Never hand-write symbols into a graph and never special-case a repo — the next repo would start from scratch, and a hand-patch vanishes on the next refresh.

Guard precision when widening a pattern. Every widening so far has nearly broken something else, and none of them were visible from the repo that motivated the change:

- A bare `^\t(name) =` for Go's grouped declarations also matches every indented key in a Lua table, taking one graph from 180 rows to 999.
- Supporting Dart's `=>` bodies made a declaration indistinguishable from a call whose last argument is a closure (`setTimeout(() => {`), adding 882 false names on svelte.
- Allowing `{` inside a signature let `export default test({` run past the newline and swallow the method below it, costing 467 files a real symbol.

So before accepting a gain, diff old against new **across every cached repo, not just the one you are fixing**, and require zero distinct symbols lost:

```bash
git show HEAD:./scripts/lib_symbols.py > /tmp/lib_symbols_old.py
# then extract with both modules over every repo in tests/.bench-cache and
# report added/lost per repo. Losses are worse than foregone gains.
```

Tune thresholds by sweeping them, not by picking a number. Report the curve you swept and where gains flatten.

## 5. Prove it

```bash
python3 tests/test_symbols.py                     # must PASS
python3 tests/bench_repo.py <every repo so far>
python3 tests/bench_locate.py <every repo so far>
```

Then add a regression test for what you fixed — a fixture in `tests/fixtures/` with expectations in `EXPECTED`, or a `PRECISION` case for a false positive. Pin the near-miss too, not just the fix: the false positive you *avoided* is the one that comes back. A fix without a test invites the same failure back.

If you added a language, add its patterns to the `PATS` table in **both** benches, or the next run will report it as perfect.

Re-run the verifier loop from step 2 across all repos, and confirm drift is still caught — inject a ghost symbol into a row's third cell and a dead path, and check each blocks. (A malformed injection reports CLEAN and looks like a broken verifier; symbols live in the **third** cell.)

The full set benchmarked so far, worth re-running when the extractor or the row policy changes: croc, winutil, PathOfBuilding-PoE2, PathOfBuilding-SimpleGraphic, find_duplicates, concat_jpeg (local, in `~/Documents`), plus AdGuardHome, copyparty, `ClassicOldSong/Apollo` (C++), svelte, fastapi, gin, buzz (Dart/Rust/TS), ego-lite, superfile. `tests/.bench-cache/` is gitignored scratch, not a fixture — it was deleted in 2026-07 (had grown to 4.2 GB) and every repo above re-clones on demand; that's expected, not a regression. Don't rebuild it as a standing cache for a small fix: for a single-pattern tweak, `tests/test_symbols.py` (no clone, covers every bug class found so far via its fixtures) plus `tests/ts_oracle.py` against one file or a fresh single-repo clone is enough. Reserve this full list for changes to the extractor's shared layers or the row-splitting policy, where a regression could hide in any language.

## 6. Commit and report

Commit with an imperative subject and a body naming the failure, the measured before/after, and the near-miss you guarded against.

Report to the user in exactly these three sections, in this order:

### 1. Problems found
What broke in the given repo(s), if anything — state plainly if nothing did; don't manufacture a finding. For each real problem: the root cause (extractor grammar gap, generator threshold, or harness bug) and which signal caught it — coverage, localization, graph size, stderr, or the verifier. Say plainly when coverage saturated and the finding came from elsewhere.

### 2. What was fixed or tuned
The change made, and why it's centralized rather than per-repo. Anything you chose not to fix, and why — include options you measured and rejected, with the number that rejected them. If nothing was fixed, say so here and skip straight to section 3.

### 3. Result: before/after
The untuned number for each new repo, first and unhedged — that is the held-out result, and it does not move even after fixes land. Then, only if something was fixed, the post-fix number alongside it for comparison. Never present a fixed-then-verified number as if it were the blind one.
