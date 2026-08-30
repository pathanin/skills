#!/usr/bin/env python3
"""Benchmark how well the graph LOCATES a symbol, not whether it mentions one.

    python3 tests/bench_locate.py <path-or-git-url> [more...]
    python3 tests/bench_locate.py --worst <repo>    # the rows that locate least

Why this exists alongside bench_repo.py. That harness asks "does this symbol
appear somewhere in the document, next to something resembling its path". Once
a language is supported the answer is yes for everything, so it pins at 100%
and stops discriminating — every repo benchmarked so far scores 100.0%.

It pins at 100% because it is a bag-of-words check over the whole file. It
cannot tell a row that narrows a symbol to one file from a row that narrows it
to sixty: both "contain" the name. But that difference is the entire value of
the graph. So this measures the search the reader is left holding:

  reach    — symbols the graph places at all (the part bench_repo.py measures)
  1-file   — symbols whose claiming row names exactly one file. The real score.
  mean/p90 — code files still to grep after consulting the graph
  misattr  — claiming row does not contain the declaration. Near zero, and kept
             as a guard: verify_graph.py only checks a symbol is *present* in
             the module, which a mere import or call satisfies, so a symbol
             declared in B and listed under A passes there and fails here.
  ln/sym   — graph lines spent per symbol, the cost side of the trade

INDEPENDENCE: the declaration patterns below are a second opinion and must
never import lib_symbols.py, for the reason given in bench_repo.py.
"""

import os
import re
import statistics
import subprocess
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
GEN = os.path.join(HERE, "..", "scripts", "build_graph.py")
CACHE = os.path.join(HERE, ".bench-cache")
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
from lib_extensions import CODE_EXT, SKIP_PARTS  # noqa: E402

SKIP_BENCH = {".git", "node_modules", "vendor", "dist", "build", "__pycache__",
              ".venv", "third_party", "external", "testdata", "deps", "docs"}
FIXTURE_PARENTS = {"samples", "fixtures", "cases", "snapshots", "__snapshots__",
                   "expected", "golden", "_output", "_expected"}

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
    # See bench_repo.py for why `{0,80}?` is bounded: unbounded, the `\s` in the
    # class makes this quadratic on C files that contain no `::` at all, which
    # is every one of the Linux kernel's 36,923. Match-identical, speed only.
    ".cpp": [r"^\s*(?:class|struct)\s+([A-Za-z_]\w*)\s*(?::|\{)",
             r"^[A-Za-z_][\w:<>,\s\*&]{0,80}?\b[A-Za-z_]\w*::([A-Za-z_~]\w*)\s*\("],
    ".swift": [r"^\s*(?:public\s+|private\s+)?func\s+([A-Za-z_]\w*)",
               r"^\s*(?:public\s+)?(?:final\s+)?(?:class|struct|enum|protocol)\s+([A-Za-z_]\w*)"],
    # Dart, added after a 237-file Flutter app scored 100% on bench_repo.py
    # while the extractor was reading 69.5% of its declarations.
    ".dart": [r"^(?:abstract\s+)?(?:class|mixin|enum|extension)\s+([A-Za-z_]\w*)",
              r"^(?:[A-Za-z_][\w<>,\s\.\?\[\]]*?)\s+([a-zA-Z_]\w*)\s*\(",
              r"^(?:final|const)\s+(?:[\w<>,\s\.\?\[\]]+\s+)?([a-zA-Z_]\w*)\s*="],
    # Plain C. See bench_repo.py: aliasing `.c` to `.cpp` expects two shapes
    # plain C never has, so a 197-file C repo offered 412 symbols instead of
    # 8,045 and every C repo read as saturated.
    ".c": [r"^[A-Za-z_][\w \t\*]{0,60}?[ \t\*]([a-z_]\w*)\s*\([^;{]*\)\s*\{",
           r"^\s*#\s*define\s+([A-Za-z_]\w*)",
           r"^\s*typedef\s+.*?\b([A-Za-z_]\w*)\s*;",
           r"^\s*(?:struct|union|enum)\s+([A-Za-z_]\w*)\s*\{"],
    # SQL DDL, absent from both benches until pi-hole — where it is the largest
    # language — was scored without it.
    ".sql": [r"(?i)^\s*CREATE\s+(?:OR\s+REPLACE\s+)?(?:UNIQUE\s+)?"
             r"(?:TEMP\s+|TEMPORARY\s+)?"
             r"(?:TABLE|VIEW|INDEX|TRIGGER|FUNCTION|PROCEDURE)\s+"
             r"(?:IF\s+NOT\s+EXISTS\s+)?[`\"\[]?([A-Za-z_]\w*)"],
    # Protocol Buffers. See bench_repo.py for why this was missing.
    ".proto": [r"^message\s+([A-Za-z_]\w*)", r"^service\s+([A-Za-z_]\w*)",
               r"^enum\s+([A-Za-z_]\w*)"],
    # `.svelte`. See bench_repo.py for why this is not a plain `.ts` alias:
    # a component's `<script>` block is conventionally indented one level, so
    # the column-0-anchored `.ts` patterns would systematically miss it.
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
BACKTICKED = re.compile(r"`([^`\n]+)`")

# Gate: below this share of symbols pinned to a single file, the graph has
# degraded into a directory index and the harness fails. Set under the current
# worst repo so an ordinary drop fails rather than passing quietly.
ONE_FILE_GATE = 0.70


def skipped(p):
    parts = p.split("/")
    if any(x in SKIP_BENCH for x in parts):
        return True
    return any(x.lower() in FIXTURE_PARENTS for x in parts[:-1])


def tracked(root):
    return subprocess.run(["git", "ls-files"], cwd=root, capture_output=True,
                          text=True).stdout.splitlines()


def blind_extensions(root):
    """{ext: file count} for extensions the generator indexes (CODE_EXT) that
    this harness has no PATS entry for -- see bench_repo.py's twin for why
    this matters: without it, a repo whose main language has no PATS entry
    produces zero `decls`, and this metric cannot tell that apart from a
    genuinely well-covered repo just by looking at the printed numbers."""
    counts = Counter()
    for f in tracked(root):
        if skipped(f):
            continue
        ext = os.path.splitext(f)[1]
        if ext in CODE_EXT and ext not in COMPILED:
            counts[ext] += 1
    return counts


def declarations(root):
    """symbol -> set of files that declare it."""
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
                n = m.group(1)
                if len(n) >= 4 and not n.startswith("_"):
                    out.setdefault(n, set()).add(f)
    return out


def parse_rows(graph):
    """[(module, {symbols})] from the Modules table."""
    rows = []
    for line in graph.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3 or set(cells[0]) <= set("-: "):
            continue
        owner = BACKTICKED.findall(cells[0])
        if not owner:
            continue
        rows.append((owner[0].strip(),
                     {s.strip() for s in BACKTICKED.findall(cells[2])}))
    return rows


def files_under(root, module, cache):
    """Code files the reader must still search after landing on `module`.

    Counted NON-recursively, and that is not a detail. build_graph.py groups by
    os.path.dirname, so a directory row owns only the files sitting directly in
    it — every subdirectory gets a row of its own. Walking the tree instead
    charged each row for its descendants' files and made the metric read
    `(repo root)` as a 7,927-file search on svelte, which would have driven the
    row-splitting thresholds off a number the generator never produced.
    """
    if module in cache:
        return cache[module]
    m = module.rstrip("/")
    if m in ("(repo root)", "."):
        m = ""
    abs_m = os.path.join(root, m)
    if os.path.isfile(abs_m):
        n = 1
    else:
        try:
            n = sum(1 for f in os.listdir(abs_m)
                    if os.path.splitext(f)[1] in CODE_EXT
                    and os.path.isfile(os.path.join(abs_m, f)))
        except OSError:
            n = 1
    cache[module] = max(n, 1)
    return cache[module]


def resolve(target):
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


def measure(root):
    graph = subprocess.run([sys.executable, GEN, root],
                           capture_output=True, text=True).stdout
    decls = declarations(root)
    claim = {}
    for mod, syms in parse_rows(graph):
        for s in syms:
            claim.setdefault(s, []).append(mod)

    cache, spaces, one, unreached, misattr, worst = {}, [], 0, 0, 0, []
    for sym, sites in decls.items():
        mods = claim.get(sym)
        if not mods:
            unreached += 1
            continue
        space = sum(files_under(root, m, cache) for m in mods)
        spaces.append(space)
        if space == 1:
            one += 1
        else:
            worst.append((space, sym, mods[0]))
        if not any(sf == m.rstrip("/") or sf.startswith(m.rstrip("/") + "/")
                   or m.rstrip("/") in ("(repo root)", ".")
                   for m in mods for sf in sites):
            misattr += 1
    n = max(len(decls), 1)
    lines = len([l for l in graph.splitlines() if l.strip()])
    return {
        "n": len(decls), "reach": 1 - unreached / n, "one": one / n,
        "mean": statistics.mean(spaces) if spaces else 0,
        "p90": sorted(spaces)[int(len(spaces) * 0.9)] if spaces else 0,
        "misattr": misattr / n, "lines": lines, "ln_per_sym": lines / n,
        "worst": sorted(worst, reverse=True)[:10],
    }


def main():
    args = [a for a in sys.argv[1:] if a != "--worst"]
    show_worst = "--worst" in sys.argv
    if not args:
        print(__doc__)
        return 2

    print(f"{'repo':<24}{'syms':>7}{'reach':>8}{'1-file':>8}{'mean':>7}"
          f"{'p90':>6}{'misattr':>9}{'ln/sym':>8}")
    print("-" * 77)
    worst_one = 1.0
    any_scored = False
    for target in args:
        root = resolve(target)
        m = measure(root)
        if m["n"] == 0:
            # No declarations at all: reach/one would print as a fake 100%/0%
            # rather than measure anything, the same trap bench_repo.py's
            # `if exp else 1.0` fell into. n/a instead, and it does not count
            # toward the gate.
            print(f"{os.path.basename(root):<24}{'n/a':>7}{'n/a':>8}{'n/a':>8}"
                  f"{'—':>7}{'—':>6}{'—':>9}{'—':>8}")
        else:
            any_scored = True
            worst_one = min(worst_one, m["one"])
            print(f"{os.path.basename(root):<24}{m['n']:>7}{m['reach']:>7.1%}"
                  f"{m['one']:>8.1%}{m['mean']:>7.1f}{m['p90']:>6.0f}"
                  f"{m['misattr']:>8.1%}{m['ln_per_sym']:>8.2f}")
        blind = blind_extensions(root)
        if blind:
            top = ", ".join(f"{ext} ({n})" for ext, n in blind.most_common(5))
            print(f"  ! no PATS expectations for: {top} -- this bench cannot "
                  "see that language; the score above does not cover it")
        if show_worst:
            for space, sym, mod in m["worst"]:
                print(f"     {space:>5} files  `{sym}` -> `{mod}`")
    print()
    if not any_scored:
        print("NO REPO PRODUCED A SCORED LANGUAGE -- add PATS entries before "
              "trusting this run")
        return 1
    ok = worst_one >= ONE_FILE_GATE
    print("PASS" if ok else
          f"BELOW GATE: worst 1-file localization {worst_one:.1%} "
          f"(gate {ONE_FILE_GATE:.0%})")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
