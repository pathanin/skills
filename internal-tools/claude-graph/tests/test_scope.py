#!/usr/bin/env python3
"""Subtree scoping and the graph-size budget.

    python3 tests/test_scope.py

Why this exists. build_graph.py used to collapse its argument straight to `git
rev-parse --show-toplevel`, so there was no way to graph part of a repo — and a
repo too large for one graph is exactly the case the tool is for. The Linux
kernel emits 65,241 rows / 130MB, 145x the largest graph in the benchmark
corpus that an agent can actually load.

Two things have to hold, and the second is the one that would rot quietly:
scoping must narrow the file set, and the paths inside a scoped graph must stay
relative to the REPO ROOT. verify_graph.py resolves the root itself and checks
every path in the graph against it, so scope-relative labels would read as dead
paths and hard-block the next Stop hook.

Exits non-zero on failure. Stdlib only.
"""

import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
import build_graph  # noqa: E402

GEN = os.path.join(HERE, "..", "scripts", "build_graph.py")


def git(args, cwd):
    subprocess.run(["git"] + args, cwd=cwd, capture_output=True, check=True)


def make_repo(d):
    """A repo with two subtrees, so scoping has something to exclude."""
    git(["init", "-q"], d)
    git(["config", "user.email", "t@t"], d)
    git(["config", "user.name", "t"], d)
    for path, body in (
        ("alpha/one.py", "def alpha_only():\n    pass\n"),
        ("alpha/two.py", "def alpha_second():\n    pass\n"),
        ("beta/three.py", "def beta_only():\n    pass\n"),
        ("top.py", "def top_level():\n    pass\n"),
    ):
        p = os.path.join(d, path)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(body)
    git(["add", "-A"], d)
    git(["commit", "-qm", "init"], d)


def make_wide_repo(d):
    """Two subtrees wide enough to clear STRUCTURE_MIN_ROWS.

    The Structure section is gated on row count, so a repo the size of
    make_repo() can only ever test the off case. This one emits a row per
    directory and crosses the gate on either subtree alone.
    """
    git(["init", "-q"], d)
    git(["config", "user.email", "t@t"], d)
    git(["config", "user.name", "t"], d)
    # `alpha` alone must clear the gate too, or the scoped case below can only
    # ever assert the off path.
    paths = [(f"alpha/m{i:02d}/x.py", f"def alpha_{i}():\n    pass\n")
             for i in range(45)]
    paths += [(f"beta/m{i:02d}/x.go", f"func Beta{i}() {{}}\n")
              for i in range(25)]
    paths.append(("top.py", "def top_level():\n    pass\n"))
    for path, body in paths:
        p = os.path.join(d, path)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(body)
    git(["add", "-A"], d)
    git(["commit", "-qm", "init"], d)


def structure_block(graph):
    """The lines of `## Structure`, exclusive of its heading and comment."""
    out, inside = [], False
    for line in graph.splitlines():
        if line.startswith("## "):
            inside = line.strip() == "## Structure"
            continue
        if inside and line.strip() and not line.lstrip().startswith("<!--"):
            out.append(line)
    return out


def run_gen(target):
    return subprocess.run([sys.executable, GEN, target],
                          capture_output=True, text=True)


def main():
    failures = []

    def check(label, cond, detail=""):
        print(f"  {'ok  ' if cond else 'FAIL'} {label}")
        if not cond:
            failures.append(f"{label}{': ' + detail if detail else ''}")

    print("IN_SCOPE — prefix matching must not fire on a sibling")
    check("exact dir", build_graph.in_scope("mm/page.c", "mm"))
    check("nested", build_graph.in_scope("mm/a/b.c", "mm"))
    check("empty scope takes everything", build_graph.in_scope("any/x.c", ""))
    # `mm` must not swallow `mmap`; a plain startswith() would.
    check("sibling with shared prefix excluded",
          not build_graph.in_scope("mmap/x.c", "mm"))
    check("unrelated excluded", not build_graph.in_scope("fs/x.c", "mm"))

    with tempfile.TemporaryDirectory() as d:
        make_repo(d)
        print("\nSCOPING — a subtree graphs only itself")
        whole = run_gen(d).stdout
        check("whole repo has both subtrees",
              "alpha_only" in whole and "beta_only" in whole)

        scoped = run_gen(os.path.join(d, "alpha")).stdout
        check("scoped graph keeps its own symbols",
              "alpha_only" in scoped and "alpha_second" in scoped)
        check("scoped graph excludes the sibling subtree",
              "beta_only" not in scoped, "beta leaked into an alpha-scoped graph")
        check("scoped graph excludes the repo root file",
              "top_level" not in scoped)

        # The property verify_graph.py depends on. Assert it on the row LABELS
        # rather than a fixed filename: a two-file directory collapses to one
        # `alpha/` row, so looking for `alpha/one.py` would test the row policy
        # rather than the path convention it means to pin.
        labels = [ln.split("|")[1].strip().strip("`")
                  for ln in scoped.splitlines()
                  if ln.startswith("| `")]
        check("scoped graph emits rows", bool(labels))
        check("every scoped row label is repo-relative",
              all(x == "alpha" or x.startswith("alpha/") for x in labels),
              f"labels are scope-relative, Stop hook would call them dead: {labels}")

        print("\nRESOLVE_SCOPE — root and subtree come apart")
        root, scope = build_graph.resolve_scope(os.path.join(d, "alpha"))
        check("root is the repo, not the subtree",
              os.path.realpath(root) == os.path.realpath(d), root)
        check("scope is the subtree", scope == "alpha", scope)
        root2, scope2 = build_graph.resolve_scope(d)
        check("whole repo has empty scope", scope2 == "", scope2)

        print("\nBUDGET — a graph that fits stays silent")
        check("no warning for a small repo",
              "claude-graph" not in run_gen(d).stderr)
        check("a bad subtree path is reported",
              "no tracked code files" in run_gen(os.path.join(d, "nope")).stderr)

        print("\nSTRUCTURE — gated off where the table is already the overview")
        check("no section on a repo under the row gate",
              "## Structure" not in run_gen(d).stdout)

    with tempfile.TemporaryDirectory() as d:
        make_wide_repo(d)
        whole = run_gen(d).stdout
        block = structure_block(whole)

        print("\nSTRUCTURE — above the gate it rolls the table up")
        check("section is emitted past the row gate", "## Structure" in whole)
        check("it names every top-level subtree",
              any("`alpha/`" in l for l in block)
              and any("`beta/`" in l for l in block), block)
        check("files at the repo root get their own entry",
              any("(repo root)" in l for l in block), block)

        # A `|` line with a backticked first cell is read as a module row by
        # verify_graph.parse_graph, bench_locate.parse_rows and
        # bench_repo.modules_only. A rollup line places no symbol, so scoring it
        # as one corrupts all three — the section has to stay a bullet list.
        check("no row of the section is a table row",
              not any(l.lstrip().startswith("|") for l in block), block)
        check("every line of the section is a bullet",
              all(l.startswith("- ") for l in block), block)

        print("\nSTRUCTURE — it appears above the table it summarises")
        check("section precedes the Modules table",
              whole.index("## Structure") < whole.index("## Modules"))

        print("\nSTRUCTURE — depth and labels follow the scope")
        scoped = run_gen(os.path.join(d, "alpha")).stdout
        sblock = structure_block(scoped)
        check("a scoped graph still gets a section", bool(sblock), scoped[:200])
        # Same property the row labels are held to: verify_graph.py resolves
        # every backticked path against the REPO ROOT, so a scope-relative
        # label here would read as a dead path and hard-block the Stop hook.
        check("every scoped section label is repo-relative",
              all(l.split("`")[1].startswith("alpha/") for l in sblock), sblock)
        check("the scoped section rolls up one level below the scope",
              any("`alpha/m00/`" in l for l in sblock), sblock)
        check("the scoped section excludes the sibling subtree",
              not any("beta" in l for l in sblock), sblock)

        print("\nSTRUCTURE — one entry is not a shape")
        check("a scope with a single child emits no section",
              "## Structure" not in run_gen(os.path.join(d, "alpha/m00")).stdout)

    print()
    if failures:
        print(f"FAILED ({len(failures)})")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
