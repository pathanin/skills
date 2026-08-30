#!/usr/bin/env python3
"""Diagnostic oracle: diff regex extraction against a tree-sitter AST.

Not part of the generator's runtime path, and not a candidate for one --
this is a manual tool for the moment a diagnosis needs ground truth stronger
than eyeballing source. This is exactly how it earned its keep in 2026-07:
comparing lib_symbols.py's Rust extraction against a real AST across a
25-repo corpus surfaced three bugs no existing gate saw --
`new`/`delete`/`default`/`from` dropped by an over-broad KEYWORDS blocklist,
Vue's `name: 'Component'` heuristic reading Go test tables and Rust data
literals as declarations, and `impl Trait for Type` misattributing the
trait name as a declaration. See git log for scripts/lib_symbols.py.

Python's entry was added the same way and found a fourth bug: a docstring's
code example (`\"\"\"...\ndef fake():...\n\"\"\"`) read as a real declaration,
since a keyword-led regex can't tell column-0 code from column-0 prose
inside a string. Confirmed and quantified with stdlib `ast` instead of this
tool, though -- for Python specifically, `ast.walk()` gives the same ground
truth as a tree-sitter grammar with zero install, so reach for that first
and treat this file's Python entry as a second, independent check.

Optional dependency, soft-detected -- nothing here runs unless invoked:

    pip install tree-sitter tree-sitter-rust tree-sitter-go

Missing tree-sitter or a language's grammar package prints one message and
exits 0; it never blocks a normal session.

Usage:

    python3 tests/ts_oracle.py <path>                  # local dir or file
    python3 tests/ts_oracle.py <git-url>                # clones to a temp dir, cleans up after
    python3 tests/ts_oracle.py <path> --lang rust        # default
    python3 tests/ts_oracle.py <path> --lang python
    python3 tests/ts_oracle.py <path> --lang go
    python3 tests/ts_oracle.py <path> --lang svelte

Prints, per file with a diff: names the regex extractor found that the
tree-sitter query didn't (either the query is incomplete, or it's a real
regex false positive worth a fixture in test_symbols.py), and names
tree-sitter found that regex didn't (a real extractor gap, or a deliberate
exclusion -- the 3-char minimum, a KEYWORDS entry -- that isn't a bug).

`rust`, `python`, `go`, and `svelte` have validated queries so far. Add a
language by adding a LANGUAGES entry: the pip package name, the file
extension, and a tree-sitter query string covering that language's
declaration node types (run `pip install tree-sitter-<lang>` and inspect a
parsed file's node kinds to find them). Do not add a language's entry
without running it against real source first -- an unvalidated query
reports differences that mean nothing.

`svelte` is a two-grammar case, and the reason its LANGUAGES entry has an
`embedded` sub-config instead of one query: tree-sitter-svelte's grammar is
HTML-shaped and returns a <script> block's contents as one opaque
`raw_text` node rather than a parsed AST -- confirmed by dumping a parsed
fixture's node kinds before writing anything. The top-level query only
locates that raw_text span; `embedded` re-parses its text with the
JavaScript grammar to actually find the declarations inside it. Any future
template-embedded language (Vue is the same shape) should expect to need
the same two-stage treatment, not a single query.
"""

import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
import lib_symbols  # noqa: E402
from lib_extensions import SKIP_PARTS  # noqa: E402

LANGUAGES = {
    "rust": {
        "ext": ".rs",
        "package": "tree_sitter_rust",
        # Deliberately excludes `impl_item` and `mod_item`: neither the regex
        # extractor nor an agent's grep treats an impl block's own target
        # type or a module path as a declaration in the sense this checks.
        "query": """
            (function_item name: (identifier) @name)
            (function_signature_item name: (identifier) @name)
            (struct_item name: (type_identifier) @name)
            (enum_item name: (type_identifier) @name)
            (trait_item name: (type_identifier) @name)
            (type_item name: (type_identifier) @name)
            (const_item name: (identifier) @name)
            (static_item name: (identifier) @name)
            (macro_definition name: (identifier) @name)
            (union_item name: (type_identifier) @name)
        """,
    },
    "python": {
        "ext": ".py",
        "package": "tree_sitter_python",
        # `function_definition`/`class_definition` match regardless of async,
        # nesting depth, or a wrapping `decorated_definition` -- confirmed by
        # parsing a sample with all four before trusting this. Deliberately
        # excludes plain module-level assignment (`CONST = 42`) and lambdas
        # bound to a name (`f = lambda: ...`): the regex extractor's own
        # SCREAMING_CASE and name=lambda GENERIC patterns already cover the
        # cases worth capturing there, so including them here would just
        # measure a difference this tool isn't meant to flag.
        "query": """
            (function_definition name: (identifier) @name)
            (class_definition name: (identifier) @name)
        """,
    },
    "go": {
        "ext": ".go",
        "package": "tree_sitter_go",
        # Every pattern is anchored `(source_file (X ...))` -- a direct child
        # of the file, not merely present anywhere in it. Without that anchor
        # this also matches `var`/`const`/`type` declared *inside* a function
        # body: confirmed on a small fixture where an unanchored query pulled
        # in `localVar`/`localConst`/`localType` from three lines inside a
        # function, none of which the regex extractor -- or an agent's grep --
        # treats as a package-level declaration. Method/function declarations
        # can't nest in Go (no local `func`/method statements), so they need
        # no such guard, but are anchored the same way for consistency.
        #
        # `type_spec` and `type_alias` are separate node kinds for `type Foo
        # struct {...}` versus `type Foo = Bar` respectively -- confirmed by
        # parsing both forms; the regex extractor's own `type` pattern doesn't
        # distinguish them, so the query must cover both to compare fairly.
        # Interface method sets (`method_elem` inside `interface_type`) and
        # struct fields (`field_declaration` inside `struct_type`) are
        # deliberately excluded: confirmed neither is a package-level name a
        # reader would grep for, the same reasoning as Rust's excluded
        # `impl_item`/`mod_item` above.
        #
        # `var` needs two shapes where `const`/`type` need only one: a single
        # `var x = 1` puts `var_spec` directly under `var_declaration`, but a
        # grouped `var (\n\tx = 1\n\ty = 2\n)` wraps every entry in an extra
        # `var_spec_list` node that `const (...)` and `type (...)` groups do
        # not add. Missing this dropped every name from any multi-entry `var
        # (...)` block -- confirmed empirically: a 4-name grouped `var` block
        # round-tripped to zero matches before this second pattern was added,
        # while the equivalent grouped `const` block worked with one pattern.
        "query": """
            (source_file (function_declaration name: (identifier) @name))
            (source_file (method_declaration name: (field_identifier) @name))
            (source_file (type_declaration (type_spec name: (type_identifier) @name)))
            (source_file (type_declaration (type_alias name: (type_identifier) @name)))
            (source_file (const_declaration (const_spec name: (identifier) @name)))
            (source_file (var_declaration (var_spec name: (identifier) @name)))
            (source_file (var_declaration (var_spec_list (var_spec name: (identifier) @name))))
        """,
    },
    "lua": {
        "ext": ".lua",
        "package": "tree_sitter_lua",
        # Anchored `(chunk ...)` for the same reason Go's patterns are: Lua
        # nests `local function` and `local x =` freely inside function
        # bodies, and neither the regex extractor nor an agent's grep treats
        # a function-body local as a file-level declaration. Unanchored, this
        # pulled `acc`/`conn` out of two function bodies in the fixture.
        #
        # `function_declaration` needs three name shapes, confirmed by
        # dumping the parsed fixture's node kinds before writing this rather
        # than assumed: a plain or `local function foo` names an `identifier`,
        # `function M.foo()` names a `dot_index_expression`, and `function
        # M:foo()` a `method_index_expression`. The latter two are distinct
        # node kinds, not a field on one -- covering only `identifier` would
        # have silently scored every table-scoped function as a miss, which
        # in idiomatic module-style Lua is most of the file.
        #
        # `variable_declaration` wraps an `assignment_statement`, so the
        # binding name sits two levels down; this is the shape that catches
        # `local fmt = function(s)` and plain `local M = {}`.
        #
        # Known, accepted difference: the oracle reports short names like `M`
        # that extract() drops via its global 3-character floor. That floor is
        # deliberate and language-independent, so it is a property of the
        # comparison, not a Lua gap.
        #
        # Read the diff on a real repo expecting asymmetry in both directions,
        # neither of which is a defect. Measured on PathOfBuilding's
        # src/Modules (28 files): 123 regex-only names, nearly all `local
        # function` helpers nested inside another function, which the `(chunk
        # ...)` anchor excludes by the same rule Go's entry uses but a
        # line-based extractor still sees; and ~12 ts-only names, all
        # top-level aliases of the form `local m_floor = math.floor`, whose
        # right-hand side is a field access rather than a function literal.
        # That second class is the same deliberate gap GENERIC's `name =
        # function` pattern documents for Svelte's `$state` — widening to a
        # bare `name = <anything>` shape is what that comment warns against,
        # so it stays open here too.
        "query": """
            (chunk (function_declaration name: (identifier) @name))
            (chunk (function_declaration name: (dot_index_expression) @name))
            (chunk (function_declaration name: (method_index_expression) @name))
            (chunk (variable_declaration (assignment_statement
                (variable_list name: (identifier) @name))))
        """,
    },
    "svelte": {
        "ext": ".svelte",
        "package": "tree_sitter_svelte",
        # Confirmed by dumping a parsed fixture's node kinds before writing
        # this: tree-sitter-svelte's grammar is HTML-shaped and does NOT
        # descend into a <script> block's contents -- they come back as one
        # opaque `raw_text` node, so a single svelte query cannot see
        # declarations at all. This query only locates that raw_text span;
        # the declarations inside it are found by re-parsing that text with
        # the JavaScript grammar, via the `embedded` config below. Two
        # grammars, not one, is why this entry doesn't fit the plain
        # {ext, package, query} shape the other three languages use.
        "query": "(script_element (raw_text) @script)",
        "embedded": {
            "package": "tree_sitter_javascript",
            # First attempt left `lexical_declaration`/`variable_declaration`
            # unanchored, matching a `let`/`const` at ANY depth -- which on
            # real svelte test fixtures (this repo's tests/ dir is full of
            # imperative test logic, not just components) pulled in every
            # loop counter and callback-local temporary: 5,638 "tree-sitter
            # only" names on the first run against the real repo, almost all
            # ordinary block-scoped locals no one greps for. `(program
            # (lexical_declaration ...))` anchors to direct children of the
            # script's top level, the same anchoring Go's query above uses
            # for the identical reason. `export let x = ...` nests the
            # declaration one level inside `export_statement`, itself a
            # direct child of `program`, so that needs its own anchored
            # variant -- confirmed by dumping a parsed fixture first.
            # function/class declarations are NOT anchored, matching
            # Python's entry above: lib_symbols.py's own patterns tolerate
            # indentation, so a nested function is a fair comparison either
            # way. `method_definition` (inside a class body) was added after
            # the first run flagged `constructor` and every other class
            # method as "regex-only" -- lib_symbols.py's own generic layer
            # already extracts indented `name(args) {` inside a class, so
            # the query was missing a real case, not the regex inventing one.
            # Known residual, not chased further: the same shorthand inside
            # a plain object expression (`return { update(name) {...} }`,
            # Svelte's action-return-value idiom) still reports as
            # regex-only, since this query has no `pair` case for it. A
            # real declaration the regex is right to keep -- the gap is in
            # this query, not in lib_symbols.py -- left open because an
            # unanchored `pair` shape risks the same nested-locals blowup
            # `lexical_declaration` hit before being anchored to `program`.
            "query": """
                (function_declaration name: (identifier) @name)
                (export_statement (function_declaration name: (identifier) @name))
                (class_declaration name: (identifier) @name)
                (export_statement (class_declaration name: (identifier) @name))
                (class_body (method_definition name: (property_identifier) @name))
                (program (lexical_declaration (variable_declarator name: (identifier) @name)))
                (program (export_statement (lexical_declaration
                    (variable_declarator name: (identifier) @name))))
                (program (variable_declaration (variable_declarator name: (identifier) @name)))
                (program (export_statement (variable_declaration
                    (variable_declarator name: (identifier) @name))))
            """,
        },
    },
}


def load_parser(lang_name):
    """(parser, query[, embedded]) for `lang_name`, or None if the grammar
    isn't installed. `embedded`, when present, is itself a (parser, query)
    pair for content the outer grammar only locates but doesn't parse --
    see the `svelte` entry above."""
    try:
        from tree_sitter import Language, Parser, Query
    except ImportError:
        return None
    spec = LANGUAGES[lang_name]
    try:
        module = __import__(spec["package"])
    except ImportError:
        return None
    language = Language(module.language())
    parser, query = Parser(language), Query(language, spec["query"])
    embed_spec = spec.get("embedded")
    if not embed_spec:
        return parser, query, None
    try:
        embed_module = __import__(embed_spec["package"])
    except ImportError:
        return None
    embed_language = Language(embed_module.language())
    embedded = (Parser(embed_language), Query(embed_language, embed_spec["query"]))
    return parser, query, embedded


def ts_extract(parser, query, raw_bytes, embedded=None):
    from tree_sitter import QueryCursor
    tree = parser.parse(raw_bytes)
    names = set()
    for _, captures in QueryCursor(query).matches(tree.root_node):
        for _, nodes in captures.items():
            for n in nodes:
                span = raw_bytes[n.start_byte:n.end_byte]
                if embedded is None:
                    names.add(span.decode(errors="ignore"))
                else:
                    embed_parser, embed_query = embedded
                    names |= ts_extract(embed_parser, embed_query, span)
    return names


def clone_if_url(path):
    if not path.startswith(("http://", "https://", "git@")):
        return path, None
    tmp = tempfile.mkdtemp(prefix="ts_oracle_")
    print(f"cloning {path} -> {tmp} ...", file=sys.stderr)
    subprocess.run(["git", "clone", "--depth", "1", "-q", path, tmp], check=True)
    return tmp, tmp


def files_under(root, ext):
    """Every file under `root` matching `ext`, filtered only by SKIP_PARTS.

    Deliberately NOT filtered by FIXTURE_PARENTS the way build_graph.py and
    both benches are: this is a diagnostic over source text, and a per-test-
    case fixture file is still real source to diff regex against tree-sitter.

    But that means a whole-directory run over a fixture-heavy repo mixes two
    very different populations. Confirmed on svelte: of 4,461 `.svelte`
    files, all but 44 sit under `samples/` trees that the generator and both
    benches collapse to one unenumerated row and never look at again -- so a
    whole-repo `ts_oracle.py --lang svelte <repo>` run reports differences in
    files nobody's score or graph ever reflects, and can look far larger or
    smaller than the real gap. Scope to the files that matter first:
        git -C <repo> ls-files '*.svelte' | grep -v '/samples/'
    then pass single files through `run()`/`files_under()` rather than the
    whole tree, if the question is "does this affect what ships."
    """
    if os.path.isfile(root):
        if root.endswith(ext):
            yield root
        return
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_PARTS]
        for f in files:
            if f.endswith(ext):
                yield os.path.join(dirpath, f)


def run(root, lang_name, parser, query, embedded=None):
    ext = LANGUAGES[lang_name]["ext"]
    total_only_regex = total_only_ts = files_checked = files_with_diff = 0
    only_regex_samples, only_ts_samples = [], []
    for path in files_under(root, ext):
        try:
            raw = open(path, "rb").read()
        except OSError:
            continue
        text = raw.decode(errors="ignore")
        files_checked += 1
        regex_names = set(lib_symbols.extract(text, ext=ext))
        ts_names = ts_extract(parser, query, raw, embedded=embedded)
        only_regex = regex_names - ts_names
        only_ts = ts_names - regex_names
        if only_regex or only_ts:
            files_with_diff += 1
        total_only_regex += len(only_regex)
        total_only_ts += len(only_ts)
        for n in only_regex:
            only_regex_samples.append((path, n))
        for n in only_ts:
            only_ts_samples.append((path, n))

    print(f"{files_checked} {ext} files, {files_with_diff} with a diff")
    print(f"regex-only (possible false positive, or query needs widening): "
          f"{total_only_regex}")
    for p, n in only_regex_samples[:20]:
        print(f"  regex-only: {n!r} <- {p}")
    print(f"tree-sitter-only (possible extractor gap, or a deliberate "
          f"exclusion -- check KEYWORDS and the 3-char minimum first): "
          f"{total_only_ts}")
    for p, n in only_ts_samples[:20]:
        print(f"  ts-only: {n!r} <- {p}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    args = sys.argv[1:]
    lang_name = "rust"
    if "--lang" in args:
        i = args.index("--lang")
        if i + 1 >= len(args):
            print("--lang needs a value")
            return 1
        lang_name = args[i + 1]
        del args[i:i + 2]
    if not args:
        print(__doc__)
        return 1
    path = args[0]

    if lang_name not in LANGUAGES:
        print(f"no query defined for {lang_name!r} -- add one to LANGUAGES "
              f"in this script, validated against real source first")
        return 1

    loaded = load_parser(lang_name)
    if loaded is None:
        pkg = LANGUAGES[lang_name]["package"].replace("_", "-")
        embed = LANGUAGES[lang_name].get("embedded")
        pkgs = pkg + (" " + embed["package"].replace("_", "-") if embed else "")
        print(f"tree-sitter or a required grammar not installed -- this is an "
              f"optional, manual diagnostic tool, not a runtime dependency.\n"
              f"  pip install tree-sitter {pkgs}")
        return 0
    parser, query, embedded = loaded

    resolved, tmp = clone_if_url(path)
    try:
        run(resolved, lang_name, parser, query, embedded=embedded)
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
