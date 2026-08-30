#!/usr/bin/env python3
"""Benchmark the generator against real repos. One command per drop.

    python3 tests/bench_repo.py <path-or-git-url> [more...]
    python3 tests/bench_repo.py --misses <repo>     # per-file diagnosis

Reports, per repo: symbol coverage, directory coverage, graph size, runtime,
and any generator warning. Clones URLs into a cache dir beside this file.

INDEPENDENCE: the expectations below are written against each language's own
grammar and must never import lib_symbols.py. The extractor is what is being
measured; if it also defined the target, the benchmark would only prove it
agrees with itself. Keep these patterns simple and readable — they are a second
opinion, not a second implementation.
"""

import os
import re
import subprocess
import sys
import time
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
GEN = os.path.join(HERE, "..", "scripts", "build_graph.py")
CACHE = os.path.join(HERE, ".bench-cache")
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
from lib_extensions import CODE_EXT  # noqa: E402

SKIP_PARTS = {".git", "node_modules", "vendor", "dist", "build", "__pycache__",
              ".venv", "third_party", "external", "testdata", "deps", "docs"}

# Per-case test-fixture trees (`tests/*/samples/<case>/…`). Excluded from the
# expectations because a name defined inside one test case is not something an
# agent navigates to — nobody greps for `option_snippet2` in
# `samples/select-with-rich-content/`. The generator collapses these trees to a
# single row on purpose; counting their contents as missed coverage would score
# that deliberate summarisation as a regression.
FIXTURE_PARENTS = {"samples", "fixtures", "cases", "snapshots", "__snapshots__",
                   "expected", "golden", "_output", "_expected"}

# ext -> declaration patterns a reader would search by
PATS = {
    ".go": [r"^func\s+(?:\([^)]*\)\s*)?([A-Za-z_]\w*)", r"^type\s+([A-Za-z_]\w*)",
            r"^(?:var|const)\s+([A-Za-z_]\w*)"],
    ".py": [r"^(?:def|class)\s+([A-Za-z_]\w*)"],
    ".ts": [r"^(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)",
            r"^(?:export\s+)?(?:abstract\s+)?class\s+([A-Za-z_$][\w$]*)",
            r"^(?:export\s+)?(?:interface|type|enum)\s+([A-Za-z_$][\w$]*)",
            r"^(?:export\s+)?const\s+([A-Za-z_$][\w$]*)\s*[:=]"],
    ".rs": [r"^(?:pub\s+)?(?:async\s+)?fn\s+([A-Za-z_]\w*)",
            r"^(?:pub\s+)?(?:struct|enum|trait)\s+([A-Za-z_]\w*)"],
    ".rb": [r"^\s*(?:def|class|module)\s+([A-Za-z_][\w:]*)"],
    ".sh": [r"^([a-z_]\w*)\s*\(\)\s*\{", r"^function\s+([A-Za-z_]\w*)"],
    ".lua": [r"^(?:local\s+)?function\s+([A-Za-z_][\w.:]*)"],
    ".ps1": [r"^\s*function\s+([A-Za-z_][\w-]*)", r"^\s*(?:class|enum)\s+([A-Za-z_]\w*)"],
    # Type declarations are barely a fifth of what a Java file declares. With
    # only the line below, Jenkins offered 3,091 expected symbols across 1,929
    # Java files and scored 99.9% while the extractor was reading 87.5% of them.
    ".java": [r"^\s*(?:public|private|protected)?\s*(?:static\s+)?(?:final\s+)?"
              r"(?:class|interface|enum)\s+([A-Za-z_]\w*)",
              r"^[ \t]+(?:(?:public|protected|private|static|final|abstract|"
              r"synchronized)\s+)+[\w<>\[\],\.]+\s+([a-z]\w*)\s*\(",
              r"^[ \t]+(?:(?:public|protected|private|static|final)\s+)+"
              r"[\w<>\[\],\.]+\s+([A-Z][A-Z0-9_]{2,})\s*="],
    # Qt's UI language. A component is named by its file; its members are
    # `property <type> <name>` and `signal`/`function`.
    ".qml": [r"^\s*(?:readonly\s+)?(?:default\s+)?property\s+[\w<>\.]+\s+([A-Za-z_]\w*)",
             r"^\s*signal\s+([A-Za-z_]\w*)",
             r"^\s*function\s+([A-Za-z_]\w*)"],
    # The `{0,80}?` bound is load-bearing, not tidiness. Unbounded (`*?`) the
    # class contains `\s`, so from every line start the engine scans forward for
    # a `::` that plain C never contains — quadratic in file size. On the Linux
    # kernel's 36,517-line `tools/testing/radix-tree/maple.c` (zero `::`) that
    # cost 4.3s per 160KB slice and rose 4x per doubling, hanging this harness
    # for over an hour before it printed a single row. Bounding the prefix caps
    # the work per line: 4.327s -> 0.012s on the same slice. Verified
    # match-identical across every cached repo (1,649 non-linux matches, 53 on
    # linux, zero lost), so it changes speed only.
    ".cpp": [r"^\s*(?:class|struct)\s+([A-Za-z_]\w*)\s*(?::|\{)",
             r"^[A-Za-z_][\w:<>,\s\*&]{0,80}?\b[A-Za-z_]\w*::([A-Za-z_~]\w*)\s*\("],
    ".swift": [r"^\s*(?:public\s+|private\s+)?func\s+([A-Za-z_]\w*)",
               r"^\s*(?:public\s+)?(?:final\s+)?(?:class|struct|enum|protocol)\s+([A-Za-z_]\w*)"],
    # Added after a Flutter monorepo scored 100% here while the extractor was
    # reading 69.5% of its 237 Dart files. With no patterns for a language, this
    # harness cannot see it at all, and reports the repo as perfect.
    ".dart": [r"^(?:abstract\s+)?(?:class|mixin|enum|extension)\s+([A-Za-z_]\w*)",
              r"^(?:[A-Za-z_][\w<>,\s\.\?\[\]]*?)\s+([a-zA-Z_]\w*)\s*\(",
              r"^(?:final|const)\s+(?:[\w<>,\s\.\?\[\]]+\s+)?([a-zA-Z_]\w*)\s*="],
    # Plain C, which this table used to alias to `.cpp` — expecting only
    # `class|struct X {` and `Foo::bar(`, two shapes plain C does not have. A
    # 197-file C repo therefore offered 412 symbols and scored a saturated 100%.
    # With the definition shape below it offers 8,045 and still scores 99.9%, so
    # the generator was never the gap here; the expectations were.
    ".c": [r"^[A-Za-z_][\w \t\*]{0,60}?[ \t\*]([a-z_]\w*)\s*\([^;{]*\)\s*\{",
           r"^\s*#\s*define\s+([A-Za-z_]\w*)",
           r"^\s*typedef\s+.*?\b([A-Za-z_]\w*)\s*;",
           r"^\s*(?:struct|union|enum)\s+([A-Za-z_]\w*)\s*\{"],
    # SQL DDL. `.sql` is in CODE_EXT, so these files reach the graph, but the
    # extension was in neither bench's table — and a language absent from it is
    # not scored at all. That hid pi-hole's largest language: 21 files and 37
    # table/view/trigger names, none of them counted either way.
    ".sql": [r"(?i)^\s*CREATE\s+(?:OR\s+REPLACE\s+)?(?:UNIQUE\s+)?"
             r"(?:TEMP\s+|TEMPORARY\s+)?"
             r"(?:TABLE|VIEW|INDEX|TRIGGER|FUNCTION|PROCEDURE)\s+"
             r"(?:IF\s+NOT\s+EXISTS\s+)?[`\"\[]?([A-Za-z_]\w*)"],
    # Protocol Buffers. `.proto` was in neither CODE_EXT nor either bench table,
    # so a repo with a substantial schema layer (worldmonitor: 284 files, 204
    # messages + 35 services) graphed as if those files did not exist.
    ".proto": [r"^message\s+([A-Za-z_]\w*)", r"^service\s+([A-Za-z_]\w*)",
               r"^enum\s+([A-Za-z_]\w*)"],
    # `.svelte` was in CODE_EXT but had no PATS entry in either bench, so the
    # svelte repo itself -- already in the named corpus -- silently scored its
    # 44 component files as if they did not exist. Not a plain `.ts` alias:
    # a component's `<script>` block is conventionally indented one level
    # (`\tconst wrapperWidth = 960;`), so the column-0-anchored `.ts` patterns
    # would systematically miss it. `\s*` tolerates that indentation; `export`
    # marks a prop, which is the closest thing a `.svelte` file has to a
    # public symbol.
    ".svelte": [r"^\s*(?:export\s+)?(?:let|const)\s+([A-Za-z_$][\w$]*)\s*[:=]",
                r"^\s*(?:export\s+)?(?:default\s+)?(?:async\s+)?"
                r"function\s+([A-Za-z_$][\w$]*)",
                r"^\s*(?:export\s+)?(?:default\s+)?class\s+([A-Za-z_$][\w$]*)"],
}
for a, b in ((".tsx", ".ts"), (".js", ".ts"), (".mjs", ".ts"), (".mts", ".ts"),
             (".cts", ".ts"), (".cjs", ".ts"), (".jsx", ".ts"),
             (".cc", ".cpp"), (".hpp", ".cpp"),
             (".psm1", ".ps1"), (".kt", ".java"), (".bash", ".sh")):
    PATS[a] = PATS[b]
# A header is either language, so it is scored against both.
PATS[".h"] = PATS[".cpp"] + PATS[".c"]
COMPILED = {e: [re.compile(p, re.M) for p in ps] for e, ps in PATS.items()}


def skipped(p):
    parts = p.split("/")
    if any(part in SKIP_PARTS for part in parts):
        return True
    # Inside a per-case fixture tree: the fixture parent is not the last
    # component, so there is a case directory beneath it.
    return any(part.lower() in FIXTURE_PARENTS for part in parts[:-1])


def norm(s):
    return re.sub(r"\s+", " ", s.lower())


def modules_only(graph):
    """Just the Modules table rows — the part of the graph that actually places
    a symbol.

    Both metrics below are bag-of-words checks, and both used to run over the
    whole document. That was safe only while every section of the graph was a
    table. It stops being safe the moment the generator emits prose that names
    directories: `locates()` ORs the symbol's `dirname` against the document, so
    a top-level rollup listing `internal/` satisfies the path half of the test
    for every symbol under it, and `dir%` counts a directory as covered when any
    line anywhere mentions it. Both would rise for a change that places nothing
    new — an instrument that reports improvement for added prose is measuring
    the prose.

    Scoping to `|` lines is the same rule bench_locate.parse_rows already
    applies, and it is why the Structure section must never be a table.
    """
    return "\n".join(l for l in graph.splitlines() if l.lstrip().startswith("|"))


def tracked(root):
    return subprocess.run(["git", "ls-files"], cwd=root, capture_output=True,
                          text=True).stdout.splitlines()


def expected(root):
    """{symbol: (path, dir)} a reader might search for."""
    out = {}
    for f in tracked(root):
        ext = os.path.splitext(f)[1]
        if ext not in COMPILED or skipped(f):
            continue
        try:
            with open(os.path.join(root, f), encoding="utf-8", errors="ignore") as fh:
                text = fh.read()
        except OSError:
            continue
        if len(text) > 2_000_000:
            continue
        for rx in COMPILED[ext]:
            for m in rx.finditer(text):
                name = m.group(1)
                if len(name) >= 4 and not name.startswith("_"):
                    out.setdefault(name, (f, os.path.dirname(f) or "."))
    return out


def blind_extensions(root):
    """{ext: file count} for extensions the generator would index (CODE_EXT)
    but this harness has no PATS entry for, among files it would actually see.

    Without this, a repo whose dominant language is one of those extensions
    produces an empty `exp` in expected(), and `cov = ... if exp else 1.0`
    silently reports a perfect, meaningless 100% -- indistinguishable in the
    printed table from a repo the extractor genuinely handles well. Sixteen
    of CODE_EXT's extensions had no PATS entry when this was added (.cs,
    .php, .scala, .zsh, .vue, .svelte, .ex/.exs, .cjs, .pl/.pm, .r, .jl,
    .m/.mm, .groovy, .tf, .hs, .zig): any repo mostly written in one of those
    would have scored 100% by construction, not by measurement. `.svelte`
    and `.cjs` were fixed alongside this (see the PATS table and the alias
    loop below); the rest are real, still-open gaps this warning now names
    instead of hiding.
    """
    counts = Counter()
    for f in tracked(root):
        if skipped(f):
            continue
        ext = os.path.splitext(f)[1]
        if ext in CODE_EXT and ext not in COMPILED:
            counts[ext] += 1
    return counts


def code_dirs(root, minfiles=3):
    counts = {}
    for f in tracked(root):
        if os.path.splitext(f)[1] not in COMPILED or skipped(f):
            continue
        d = os.path.dirname(f) or "."
        counts[d] = counts.get(d, 0) + 1
    return sorted(d for d, n in counts.items() if n >= minfiles and d != ".")


def locates(ndoc, sym, path, dirname):
    """`ndoc` is the ALREADY-normalised graph. Normalising it here instead cost
    a full `re.sub` over the whole document once per symbol: on the Linux
    kernel that is 105,062 symbols x a ~40MB graph, and the harness ran 78
    minutes and 6.7GB before being killed without printing a row. Same
    arithmetic on a small repo hides it — 4,000 symbols x 200KB is a few
    seconds. Hoisting is behaviour-preserving; `norm` is deterministic."""
    if norm(sym) not in ndoc:
        return False
    base = os.path.basename(path)
    stem = os.path.splitext(base)[0]
    return any(norm(x) in ndoc
               for x in (path, base, stem, dirname) if x and x != ".")


def resolve(target):
    """Local path, or clone the URL into the cache and return that path."""
    if not target.startswith(("http://", "https://", "git@")):
        return os.path.abspath(target)
    name = target.rstrip("/").split("/")[-1].removesuffix(".git")
    dest = os.path.join(CACHE, name)
    if not os.path.isdir(dest):
        os.makedirs(CACHE, exist_ok=True)
        print(f"  cloning {name}...", file=sys.stderr)
        subprocess.run(["git", "clone", "--depth", "1", "-q", target, dest],
                       check=True)
    return dest


def run(root):
    started = time.time()
    proc = subprocess.run([sys.executable, GEN, root], capture_output=True, text=True)
    return proc.stdout, proc.stderr.strip(), time.time() - started


def main():
    args = [a for a in sys.argv[1:] if a != "--misses"]
    show_misses = "--misses" in sys.argv
    if not args:
        print(__doc__)
        return 2

    print(f"{'repo':<24}{'files':>7}{'symbols':>9}{'sym%':>8}{'dir%':>7}"
          f"{'graph':>7}{'sec':>6}")
    print("-" * 68)
    worst = 1.0
    any_scored = False
    for target in args:
        root = resolve(target)
        name = os.path.basename(root)
        graph, warn, secs = run(root)
        exp = expected(root)
        dirs = code_dirs(root)
        ngraph = norm(modules_only(graph))
        hits = {s for s, (p, d) in exp.items() if locates(ngraph, s, p, d)}
        dh = sum(1 for d in dirs if norm(d) in ngraph)
        lines = len([l for l in graph.splitlines() if l.strip()])
        dirpct = f"{(dh / len(dirs) if dirs else 1):>6.0%}"
        if exp:
            cov = len(hits) / len(exp)
            worst = min(worst, cov)
            any_scored = True
            covstr = f"{cov:>7.1%}"
        else:
            # No PATS expectations at all for this repo's languages: a
            # coverage number here would be vacuous, not a measurement, so
            # print n/a and leave the pass/fail gate untouched by it.
            covstr = f"{'n/a':>7}"
        print(f"{name:<24}{len(tracked(root)):>7}{len(exp):>9}{covstr}"
              f"{dirpct}{lines:>7}{secs:>6.1f}")
        if warn:
            print(f"  ! {warn.splitlines()[0][:100]}")
        blind = blind_extensions(root)
        if blind:
            top = ", ".join(f"{ext} ({n})" for ext, n in blind.most_common(5))
            print(f"  ! no PATS expectations for: {top} -- this bench cannot "
                  "see that language; the score above does not cover it")
        if show_misses and len(hits) < len(exp):
            miss = Counter(exp[s][0] for s in exp if s not in hits)
            for path, n in miss.most_common(8):
                names = [s for s in exp if s not in hits and exp[s][0] == path][:5]
                print(f"     {n:>4}  {path}   {names}")
    print()
    if not any_scored:
        print("NO REPO PRODUCED A SCORED LANGUAGE -- add PATS entries before "
              "trusting this run")
        return 1
    print("PASS" if worst >= 0.98 else f"BELOW GATE: worst coverage {worst:.1%}")
    return 0 if worst >= 0.98 else 1


if __name__ == "__main__":
    sys.exit(main())
