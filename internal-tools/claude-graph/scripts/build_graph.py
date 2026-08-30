#!/usr/bin/env python3
"""Emit a skeleton .claude/graph.md: every module, every public symbol.

Symbol selection must be exhaustive, not curated — a hand-picked "key symbols"
list is what makes a graph fail at its one job. This script does the extraction
so the model only writes the judgment parts (`Owns`, `Depends on`, routing).

    python3 build_graph.py [repo_root] > /tmp/graph.skeleton.md

Prints TODO markers where judgment is required. Stdlib only.
"""

import os
import re
import subprocess
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# Source-file selection is shared with verify_graph.py; see lib_extensions.py
# for why it must not be duplicated.
from lib_extensions import CODE_EXT, SKIP_PARTS  # noqa: E402

# Symbol extraction lives in lib_symbols.py: language-specific patterns plus a
# generic layer that reads declaration *shapes* rather than languages. See that
# module's docstring for why, and tests/test_symbols.py for the conformance
# gate that keeps it honest.
from lib_symbols import extract as _extract  # noqa: E402

# A line that closes a parameter list and opens a block: what a definition looks
# like in C-family, keyword-first, and def-style languages alike.
CALLABLE_LINE = re.compile(
    r"^[^\s#/*].*\)\s*(?:const\s*)?(?:noexcept\s*)?[{:]\s*$", re.M)
BLIND_SHARE = 0.30

# A directory dense enough that one row would bury the reader is split into
# file-level rows instead.
#
# Both thresholds are set by measuring what the graph is for: locating a symbol.
# A directory row answers "which file?" with "one of these N", so N is the grep
# the reader still has to run. Coverage cannot see this — it scores a name as
# found whether the row narrows it to one file or to sixty — so it was measured
# separately (tests/bench_locate.py). At the old (40, unbounded) setting, 34%
# of symbols resolved only to a directory; on svelte the average symbol landed
# in a 118-file row and on winutil the 90th percentile was a 33-file grep.
FILE_ROW_THRESHOLD = 12
# The file-count rule is what fixed that: splitting on symbol count alone left a
# 12-file directory holding 30 symbols as a single row. Past ~5 files a
# directory row has stopped locating anything.
FILE_COUNT_THRESHOLD = 5
# No per-file symbol cap: truncating is the failure this generator exists to
# prevent. Benchmarked on a 1,896-file repo, a 25-symbol cap silently dropped
# 185 symbols — every one of them in a file the graph already named, so the row
# looked complete while sending the agent to grep anyway.
#
# Directories that hold data or assets rather than code get a single row with no
# symbol list; enumerating 754 stat-description files buys nothing.
DATA_DIR_HINTS = ("data", "assets", "fixtures", "testdata", "locale", "i18n",
                  "migrations", "static", "public", "docs")


def sh(args, cwd):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True).stdout


def skipped(p):
    return any(part in p.split("/") for part in SKIP_PARTS)


def read_source(path):
    """File text, or None if unreadable/too large. Cached: the symbol pass and
    the unsupported-language check both need it, and re-reading a 1,896-file
    repo doubles runtime for nothing."""
    if path in _SOURCE_CACHE:
        return _SOURCE_CACHE[path]
    try:
        if os.path.getsize(path) > 2_000_000:
            text = None
        else:
            with open(path, encoding="utf-8", errors="ignore") as fh:
                text = fh.read()
    except OSError:
        text = None
    _SOURCE_CACHE[path] = text
    return text


_SOURCE_CACHE = {}


def symbols_in(path):
    text = read_source(path)
    if not text:
        return []
    return _extract(text, ext=os.path.splitext(path)[1])


FIXTURE_PARENTS = ("samples", "fixtures", "cases", "snapshots", "__snapshots__",
                   "expected", "golden", "input", "output", "_output")
FIXTURE_MIN_CHILDREN = 12


def collapse_fixture_trees(by_dir):
    """{root: (label, files, dirs)} for per-case test-fixture trees.

    A test suite with one directory per case — `tests/*/samples/<case>/` — emits
    one row per case. On a repo with 8,211 files under such trees that produced
    a 6,793-line graph of which 91% of rows were fixtures: technically complete,
    useless to read, and invisible to a coverage metric because the real code
    still scored 100%.

    Collapsing needs the *parent* (`samples/`), not each case, and only when
    there are many sibling cases — a handful of fixture dirs is worth listing.
    Test code itself is untouched; only the case trees beneath a fixture parent
    collapse, so `tests/` and its helpers still get real rows.
    """
    children = defaultdict(list)
    for d in by_dir:
        parts = d.split("/")
        for i, part in enumerate(parts[:-1]):
            if part.lower() in FIXTURE_PARENTS:
                children["/".join(parts[:i + 1])].append(d)
                break
    out = {}
    for root, dirs in children.items():
        if len(dirs) < FIXTURE_MIN_CHILDREN:
            continue
        n = sum(len(by_dir[d]) for d in dirs) + len(by_dir.get(root, []))
        out[root] = (f"{root}/", n, len(dirs))
    return out


def unsupported_languages(root, files, syms_by_file):
    """Extensions whose definition-bearing files yielded no symbols.

    Two weaker signals were measured and rejected. *Zero symbols per extension*
    never fires: the generic `class X` pattern still caught type names in
    unsupported C++, so it looked partly alive. *Symbols per KB* cannot
    discriminate either — broken C++ scored 0.42-0.51 per 10KB against healthy
    Lua's 0.54, because that repo is 96% data tables.

    What separates them is asking only about files that *look like they define
    callables*. Data tables and spec files never do, so they drop out of the
    denominator instead of diluting it. On the C++ repo this read 33-83% blind
    before the C-family patterns existed and 0% after, while Lua and Python
    registered no qualifying files at all.
    """
    by_ext = defaultdict(lambda: [0, 0])  # ext -> [callable-ish files, blind]
    for f in files:
        # A file that already yielded symbols proves the language is supported,
        # so only the silent ones need the (comparatively costly) scan.
        if syms_by_file.get(f):
            by_ext[os.path.splitext(f)[1]][0] += 1
            continue
        path = os.path.join(root, f)
        text = read_source(path)
        if not text or len(text) < 2048:
            continue
        if len(CALLABLE_LINE.findall(text)) < 3:
            continue
        stat = by_ext[os.path.splitext(f)[1]]
        stat[0] += 1
        stat[1] += 1
    return sorted(ext for ext, (n, blind) in by_ext.items()
                  if n >= 3 and blind / n > BLIND_SHARE)


# A graph is only worth generating if it can be loaded into context — that is
# the entire delivery mechanism. Measured across the benchmark corpus, the
# largest graph that still works is buzz at 2,504 rows / 898KB, and every other
# repo lands well under it (jenkins 2,079/575KB, Pumpkin 1,689/460KB, svelte
# 554/377KB). The Linux kernel emits 65,241 rows / 130MB — 145x the largest
# working graph, for the exact case this tool exists to serve. Neither gate sees
# it: coverage saturates and localization passes at 88%.
#
# So the budget is set just above the whole corpus rather than at a round
# number, and going over is not an error — the graph is still emitted. It is a
# warning that names the subtrees to scope to, because a 130MB file that no
# agent can read is worse than several that they can.
GRAPH_ROW_BUDGET = 3000
GRAPH_BYTE_BUDGET = 1_000_000


def oversized(root, scope, files, rows):
    """Warn, and name the subtrees worth graphing separately."""
    nbytes = sum(len(r) + 1 for r in rows)
    if len(rows) <= GRAPH_ROW_BUDGET and nbytes <= GRAPH_BYTE_BUDGET:
        return
    depth = len(scope.split("/")) if scope else 0
    counts = defaultdict(int)
    for f in files:
        parts = f.split("/")
        if len(parts) > depth + 1:
            counts["/".join(parts[:depth + 1])] += 1
    top = sorted(counts.items(), key=lambda kv: -kv[1])[:5]
    where = f"`{scope}`" if scope else "this repo"
    sys.stderr.write(
        f"claude-graph: the graph for {where} is {len(rows)} rows / "
        f"{nbytes / 1e6:.1f}MB, past the {GRAPH_ROW_BUDGET}-row / "
        f"{GRAPH_BYTE_BUDGET / 1e6:.1f}MB budget a graph has to fit to be "
        "loadable at all. It was still written, but an agent cannot read it. "
        "Generate one per subtree instead:\n"
        + "".join(f"    build_graph.py {os.path.join(root, d)}"
                  f"   ({n} code files)\n" for d, n in top)
        + "Paths stay repo-relative, so each scoped graph still verifies "
          "against the repo root.\n")


# Orientation, not navigation. The Modules table answers "where is X"; past a
# few hundred rows nothing in the graph answers "what is this repo shaped like",
# and the reader has to infer it by scanning the Path column. This rolls the
# same file set up to one line per top-level subtree.
#
# It is a BULLET LIST and must never become a table. A `|` line whose first cell
# is a backticked path is read as a module row by verify_graph.parse_graph
# (which would then hunt for the third cell's "symbols" in the source),
# by bench_locate.parse_rows, and by bench_repo.modules_only. A rollup line
# places no symbol, so admitting it to any of those corrupts the measurement —
# see bench_repo.modules_only for the metric that breaks first.
#
# Below this many module rows the table is already the overview: on a 99-row
# graph a rollup restates the Path column, which is cost with no orientation
# bought. The gate is what makes this free where it would not pay.
STRUCTURE_MIN_ROWS = 40
STRUCTURE_TOP_EXTS = 3


def structure(scope, files, rows):
    """The `## Structure` block, or [] when it would not pay for itself.

    Depth is relative to `scope`, the same arithmetic oversized() uses: a graph
    scoped to `mm` must roll up `mm/*`, not the kernel's top level, or a scoped
    graph gets a one-line section naming only itself.

    Every field is mechanical — counts and extensions, no TODO. That is what
    lets the refresh path regenerate this section wholesale instead of needing
    a merge rule beside `Owns` and `Depends on`, which is the form of judgment
    text that rots.
    """
    if len(rows) < STRUCTURE_MIN_ROWS:
        return []
    depth = len(scope.split("/")) if scope else 0
    groups = defaultdict(list)
    for f in files:
        parts = f.split("/")
        # Files sitting directly at the scope root have no subtree of their own.
        groups["/".join(parts[:depth + 1]) if len(parts) > depth + 1 else ""] \
            .append(f)
    # One entry is not a shape, it is the same claim the scope line already
    # makes.
    if len(groups) < 2:
        return []

    # verify_graph.parse_graph matches this heading by name to keep these paths
    # out of its coverage set. Rename it there too, or the exclusion silently
    # stops firing.
    out = ["## Structure",
           "<!-- Mechanical rollup of the table below; regenerated wholesale. -->"]
    for key, gfiles in sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        exts = Counter(os.path.splitext(f)[1] for f in gfiles)
        top = ", ".join(f"`{e}`" for e, _ in exts.most_common(STRUCTURE_TOP_EXTS))
        if key:
            label = f"`{key}/`"
        elif scope:
            label = f"`{scope}/`"
        else:
            label = "(repo root)"
        ndirs = len({os.path.dirname(f) for f in gfiles})
        where = f" in {ndirs} dirs" if ndirs > 1 else ""
        noun = "code file" if len(gfiles) == 1 else "code files"
        out.append(f"- {label} — {len(gfiles)} {noun}{where} · {top}")
    out.append("")
    return out


def resolve_scope(target):
    """(repo root, subtree) for `target`, which may be a subdirectory.

    The argument used to be collapsed straight to `git rev-parse
    --show-toplevel`, so pointing this at `linux/drivers/net` silently graphed
    all 94,850 files of the kernel. There was no way to scope a graph at all,
    which is the whole workaround for a repo too large to fit in one — and this
    tool exists for large repos.

    Paths stay relative to the REPO ROOT, not the subtree. verify_graph.py
    resolves the root itself and checks every path in the graph against it, so
    scope-relative labels would read as dead paths on the next Stop hook.
    """
    # realpath on BOTH sides, not abspath. `git rev-parse` reports the resolved
    # path, so on macOS — where /tmp and /var are symlinks — comparing it to an
    # unresolved argument yields a scope of `../../../private/var/...` and the
    # graph comes out empty. Anyone working under those paths would hit it.
    target = os.path.realpath(target)
    probe = target if os.path.isdir(target) else os.path.dirname(target)
    root = sh(["git", "rev-parse", "--show-toplevel"], probe).strip() or probe
    root = os.path.realpath(root)
    scope = os.path.relpath(target, root).replace(os.sep, "/")
    if scope == "." or scope.startswith(".."):
        # Outside the repo, or the repo root itself: graph everything.
        return root, ""
    return root, scope


def in_scope(path, scope):
    return not scope or path == scope or path.startswith(scope + "/")


def main():
    root, scope = resolve_scope(sys.argv[1] if len(sys.argv) > 1 else ".")
    files = [f for f in sh(["git", "ls-files"], root).splitlines()
             if f and not skipped(f) and os.path.splitext(f)[1] in CODE_EXT
             and in_scope(f, scope)]
    if scope and not files:
        sys.stderr.write(
            f"claude-graph: no tracked code files under `{scope}`. Check the "
            "path, or drop it to graph the whole repo.\n")

    by_dir = defaultdict(list)
    for f in files:
        by_dir[os.path.dirname(f) or "."].append(f)

    all_syms = {f: symbols_in(os.path.join(root, f)) for f in files}
    if not files:
        # No recognized source at all. CODE_EXT is missing this repo's language,
        # and unsupported_languages() cannot help: it only inspects files that
        # were read in the first place, so an unknown extension is a silent
        # zero. A PowerShell repo emitted an empty table this way.
        counts = defaultdict(int)
        for f in sh(["git", "ls-files"], root).splitlines():
            if f and not skipped(f) and in_scope(f, scope):
                counts[os.path.splitext(f)[1]] += 1
        common = ", ".join(
            f"{ext or '(no ext)'} ({n})"
            for ext, n in sorted(counts.items(), key=lambda kv: -kv[1])[:5])
        sys.stderr.write(
            "claude-graph: no files with a recognized code extension. The graph "
            "will be empty. Most common extensions here: " + common
            + ". Add the right one to CODE_EXT in build_graph.py, with a "
              "matching pattern in lib_symbols.py, and regenerate.\n")
    blind = unsupported_languages(root, files, all_syms)
    if blind:
        sys.stderr.write(
            "claude-graph: files defining functions in "
            + ", ".join(blind)
            + " yielded no symbols. lib_symbols.py likely has no pattern for "
              "this language, so those rows will name the right files and "
              "locate nothing in them. Add a pattern there, add a fixture to "
              "tests/, and regenerate before trusting the graph.\n")

    # Computed before Entry points, not just Modules, because a fixture case
    # file (`tests/compiler-errors/samples/<case>/main.svelte`) matches the
    # "main."/"index." entry-point heuristic just as readily as a real one.
    # On svelte this alone put 2,678 per-test-case `main.svelte` fixtures
    # into "## Entry points" — 83% of the whole graph's line count, none of
    # them a process entry point an agent would ever start reading from.
    fixture_roots = collapse_fixture_trees(by_dir)

    def in_fixture_tree(f):
        d = os.path.dirname(f) or "."
        return any(d == r or d.startswith(r + "/") for r in fixture_roots)

    # Rows are built before anything is printed: the Structure section is gated
    # on how many there turn out to be, and it has to appear above the table it
    # summarises.
    rows = []
    collapsed = []
    for label, n, dirs_n in sorted(fixture_roots.values()):
        collapsed.append((label, n, f"{dirs_n} fixture dirs"))
    for d in sorted(by_dir):
        if any(d == r or d.startswith(r + "/") for r in fixture_roots):
            continue
        dfiles = sorted(by_dir[d])
        syms_by_file = {f: all_syms[f] for f in dfiles}
        allsyms = [s for f in dfiles for s in syms_by_file[f]]
        label = f"{d}/" if d != "." else "(repo root)"

        # A directory of data/assets: one row, no enumeration. Judged by the
        # symbols actually found, not by name alone, so a code directory that
        # happens to be called `static/` is still listed properly.
        if not allsyms and d != ".":
            parts = {p.lower() for p in d.split("/")}
            # Never collapse tests: the routing table has to name where a test
            # goes, and a test directory legitimately declares no symbols.
            is_test = bool(parts & {"test", "tests", "spec", "specs", "__tests__"})
            if not is_test and (parts & set(DATA_DIR_HINTS) or len(dfiles) > 8):
                collapsed.append((label, len(dfiles), "data/asset files"))
                continue

        if len(dfiles) > 1 and (len(allsyms) > FILE_ROW_THRESHOLD
                                or len(dfiles) > FILE_COUNT_THRESHOLD):
            # Too dense for one row: one row per file, every symbol kept.
            for f in dfiles:
                cell = ", ".join(f"`{s}`" for s in syms_by_file[f]) or "—"
                rows.append(f"| `{f}` | TODO | {cell} | TODO |")
        else:
            cell = ", ".join(f"`{s}`" for s in allsyms) or "—"
            files_note = ", ".join(f"`{os.path.basename(f)}`" for f in dfiles[:6])
            rows.append(f"| `{label}` | TODO ({files_note}) | {cell} | TODO |")

    for entry in collapsed:
        label, n = entry[0], entry[1]
        kind = entry[2] if len(entry) > 2 else "data/asset files"
        rows.append(f"| `{label}` | TODO — {n} files in {kind}, not enumerated "
                    f"| — | TODO |")

    print("<!-- generated: TODO date @ TODO sha — when this disagrees with the "
          "repo, the repo wins: fix the row. -->\n")
    for line in structure(scope, files, rows):
        print(line)
    print("## Entry points")
    print("<!-- TODO: name each real entry point and what it wires together. -->")
    for f in sorted(files):
        if in_fixture_tree(f):
            continue
        base = os.path.basename(f).lower()
        if base.startswith(("main.", "index.", "cli.", "app.", "launch.")) or \
           os.path.splitext(base)[0] == os.path.basename(root).lower():
            print(f"- `{f}` — TODO")
    print()

    print("## Modules")
    print("| Path | Owns | Key symbols | Depends on |")
    print("|---|---|---|---|")
    for r in rows:
        print(r)
    print()
    print("## Where do I add X?")
    print("<!-- TODO: one line per recurring task; name the file to touch. -->")
    oversized(root, scope, files, rows)


if __name__ == "__main__":
    main()
