#!/usr/bin/env python3
"""Regression guard for verify_graph.py's dead-path check.

    python3 tests/test_verify.py

A bracketed path — `[hostId]`, `[worktreeId].tsx` — is Next.js/SvelteKit/Expo
Router's dynamic-route convention, written straight into the filesystem. The
dead-path check used to route any path containing `[` through `glob.glob`,
which reads the bracket as a character class instead of literal text, so a
real, tracked file at that path matched nothing and was reported dead. That is
a false block on every Stop hook for any repo using the convention: it hit 2
of 3 repos in one benchmark batch (orca, worldmonitor).

Exits non-zero on failure. Stdlib only.
"""

import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
import verify_graph  # noqa: E402

GEN = os.path.join(HERE, "..", "scripts", "build_graph.py")

TABLE_HEADER = "## Modules\n| Path | Owns | Key symbols | Depends on |\n|---|---|---|---|\n"


def git(args, cwd):
    subprocess.run(["git"] + args, cwd=cwd, capture_output=True, check=True)


def make_repo(d):
    git(["init", "-q"], d)
    git(["config", "user.email", "t@t"], d)
    git(["config", "user.name", "t"], d)
    for path, body in (
        ("app/h/[hostId]/accounts.tsx", "export function Accounts() {}\n"),
        ("app/w/[worktreeId].tsx", "export function Worktree() {}\n"),
        ("src/one.ts", "export function one() {}\n"),
        # Three files, so this directory clears UNMAPPED_MIN_FILES and the
        # SessionStart advisory has something it can legitimately flag.
        ("lib/a.ts", "export function libA() {}\n"),
        ("lib/b.ts", "export function libB() {}\n"),
        ("lib/c.ts", "export function libC() {}\n"),
    ):
        p = os.path.join(d, path)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(body)
    git(["add", "-A"], d)
    git(["commit", "-qm", "init"], d)


def make_split_repo(d):
    """Wide enough for `## Structure`, with one directory dense enough that the
    generator splits it into per-file rows and emits no directory row for it.

    That combination is what the end-to-end check needs: `alpha/dense` is then
    covered by nothing but the `alpha/` line in Structure.
    """
    git(["init", "-q"], d)
    git(["config", "user.email", "t@t"], d)
    git(["config", "user.name", "t"], d)
    paths = [(f"alpha/m{i:02d}/x.py", f"def alpha_{i}():\n    pass\n")
             for i in range(45)]
    paths += [(f"alpha/dense/f{i}.py", f"def dense_{i}():\n    pass\n")
              for i in range(8)]
    paths += [(f"beta/m{i:02d}/x.py", f"def beta_{i}():\n    pass\n")
              for i in range(6)]
    for path, body in paths:
        p = os.path.join(d, path)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(body)
    git(["add", "-A"], d)
    git(["commit", "-qm", "init"], d)


def write_graph(root, rows, structure=""):
    d = os.path.join(root, ".claude")
    os.makedirs(d, exist_ok=True)
    head = f"## Structure\n{structure}\n" if structure else ""
    with open(os.path.join(d, "graph.md"), "w", encoding="utf-8") as fh:
        fh.write(head + TABLE_HEADER + rows)


def main():
    failures = []

    def check(label, cond, detail=""):
        print(f"  {'ok  ' if cond else 'FAIL'} {label}")
        if not cond:
            failures.append(f"{label}{': ' + detail if detail else ''}")

    with tempfile.TemporaryDirectory() as d:
        make_repo(d)

        print("BRACKET PATHS — dynamic-route names are literal, not glob")
        write_graph(d,
            "| `app/h/[hostId]/accounts.tsx` | TODO | `Accounts` | TODO |\n"
            "| `[worktreeId].tsx` | TODO (`[worktreeId].tsx`) | `Worktree` | TODO |\n")
        dead_paths, _, _ = verify_graph.check(d)
        check("a real nested bracket path is not reported dead",
              "app/h/[hostId]/accounts.tsx" not in dead_paths, dead_paths)
        check("a real bare bracket filename is not reported dead",
              "[worktreeId].tsx" not in dead_paths, dead_paths)

        print("\nDEAD BRACKET PATH — a genuinely gone one is still caught")
        write_graph(d, "| `app/h/[deletedRoute]/gone.tsx` | TODO | `Gone` | TODO |\n")
        dead_paths, _, _ = verify_graph.check(d)
        check("a genuinely dead bracket path is still reported dead",
              "app/h/[deletedRoute]/gone.tsx" in dead_paths, dead_paths)

        print("\nGLOB PATTERN — `*`/`?` still resolve as patterns, both ways")
        write_graph(d, "| `src/*.ts` | TODO | `one` | TODO |\n")
        dead_paths, _, _ = verify_graph.check(d)
        check("a real glob pattern still resolves",
              "src/*.ts" not in dead_paths, dead_paths)

        write_graph(d, "| `src/*.nope` | TODO | `one` | TODO |\n")
        dead_paths, _, _ = verify_graph.check(d)
        check("a glob pattern matching nothing is still reported dead",
              "src/*.nope" in dead_paths, dead_paths)

        print("\nSTRUCTURE SECTION — checked for rot, but never counts as coverage")
        row = "| `src/one.ts` | TODO | `one` | TODO |\n"
        write_graph(d, row, "- `lib/` — 3 code files · `.ts`\n")
        dead_paths, _, unmapped = verify_graph.check(d)
        check("a live Structure path is not reported dead",
              "lib" not in dead_paths and "lib/" not in dead_paths, dead_paths)
        # The whole point of the exclusion. `## Structure` is a rollup, so one
        # `src/` line there would answer the unmapped check for every directory
        # beneath it and the advisory would go permanently silent — the repo
        # would look guarded while nothing was being checked.
        check("a directory named ONLY in Structure is still unmapped",
              "lib" in unmapped, unmapped)

        write_graph(d, row + "| `lib/` | TODO | `libA` | TODO |\n",
                    "- `lib/` — 3 code files · `.ts`\n")
        _, _, unmapped = verify_graph.check(d)
        check("a directory with a real table row is mapped",
              "lib" not in unmapped, unmapped)

        write_graph(d, row, "- `gone/` — 4 code files · `.ts`\n")
        dead_paths, _, _ = verify_graph.check(d)
        check("a dead Structure path is still reported dead",
              "gone" in dead_paths, dead_paths)

    with tempfile.TemporaryDirectory() as d:
        make_split_repo(d)
        graph = subprocess.run([sys.executable, GEN, d],
                               capture_output=True, text=True).stdout
        os.makedirs(os.path.join(d, ".claude"), exist_ok=True)
        with open(os.path.join(d, ".claude", "graph.md"), "w",
                  encoding="utf-8") as fh:
            fh.write(graph)
        _, _, unmapped = verify_graph.check(d)

        # End-to-end, against a graph the generator actually wrote. The two
        # files agree only by the literal heading name, so a rename on either
        # side disables the exclusion with no traceback — this is what fails
        # when that happens. `alpha/dense` is split into per-file rows and so
        # has no directory row of its own; `## Structure` names `alpha/`, which
        # would cover it by prefix if Structure counted as coverage.
        print("\nGENERATED GRAPH — the heading contract holds end to end")
        check("the generated graph has a Structure section",
              "## Structure" in graph)
        check("Structure names the parent subtree",
              "`alpha/`" in graph, [l for l in graph.splitlines()
                                    if l.startswith("- ")])
        check("a split directory under it is still reported unmapped",
              "alpha/dense" in unmapped, unmapped)

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
