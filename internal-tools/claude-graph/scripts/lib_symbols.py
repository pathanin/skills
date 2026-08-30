#!/usr/bin/env python3
"""Symbol extraction: language-specific patterns plus a generic fallback layer.

Design note — why the generic layer exists.

Three held-out benchmarks each caught the generator failing on a language it had
not seen: C++ scored 13%, PowerShell 0%, Go/TypeScript 84%. Each was fixed by
hand-writing another regex, which is an unbounded tail: measured against 20
languages nobody had written rules for, per-language patterns alone resolved
26% of declarations.

So the second layer below does not encode any single language. It encodes the
*shapes* declarations take across languages — a keyword from a large set
followed by a name, an assignment whose right side is a function, a
parenthesised signature followed by a brace, a type signature, a DDL statement,
an HCL block. On those same 20 unseen languages this layer takes recall from
26% to 96% without a rule for any of them.

Precision is protected three ways, each of which fixed an observed false
positive: KEYWORDS excludes declaration keywords that one language's syntax
turns into another's identifier; the keyword-led pattern requires a full
identifier including hyphens, so PowerShell's `Get-WinUtilThing` yields the
whole name rather than the verb `Get`; and `package`/`import`/`namespace` are
not treated as declaring a searchable symbol, since a package name is not
something an agent greps for.
"""

import io
import re
import tokenize

# Definition keywords, from every language family this has been tested against
# plus the obvious neighbours. Deliberately broad: a false keyword costs one
# spurious name, a missing one costs an entire language.
_DECL = ("class|interface|trait|protocol|object|module|namespace|"
         "record|data|newtype|impl|actor|mixin|extension|contract|"
         "def|defn|defmodule|defmacro|defp|defstruct|defprotocol|"
         "func|fn|function|sub|method|proc|procedure|macro")
# Split out of _DECL because these four are the only ones that appear as often
# at a *use* site as at a declaration: `struct list_head list;` uses the type,
# it does not declare it. Folded in with the rest, they made the keyword-led
# pattern emit a type name in every file that merely mentions it — on the Linux
# kernel `device` landed in 8,565 files, `of_device_id` 6,045, `platform_driver`
# 5,611. Since bench_locate.py scores a symbol as located only when one row
# claims it, that alone held 1-file localization to 47.8% against a 95.4%
# ceiling. See _USE_GUARD for how the two are told apart.
_DECL_TYPE = "struct|union|enum|typedef"
_MOD = (r"(?:(?:public|private|protected|internal|static|final|abstract|"
        r"open|sealed|override|virtual|inline|export|default|pub(?:\([^)]*\))?|"
        r"async|const|suspend|operator|data|case|lazy|extern|unsafe|"
        r"partial|readonly|companion|local|@\w+)\s+)*")

# A return type, as it appears just before a function name.
#
# Deliberately confined to one line: `[ \t]` rather than `\s`. With `\s` the
# non-greedy class could run across newlines, which made this pattern quadratic
# on generic-heavy source — extracting Pumpkin took 22.7s, more than the whole
# rest of the suite. Bounding it to a single line cut that to 4.0s, below even
# the pre-change 10.5s. Nothing real was lost: the only matches that needed a
# newline were ones starting on a `template<class T>` line above the signature,
# and the `[[attr]]` / `::` prefixes below pick those up properly instead.
_TYPE = r"(?:\[\[[\w:,\s]+\]\][ \t]*)?(?:::)?[A-Za-z_][\w:<>,\[\]\.\*&? \t]*?"

# Language-specific patterns. Kept because they are precise where they apply:
# they anchor to column 0 and to a known grammar, so they carry less risk than
# the generic layer on the languages they cover.
SPECIFIC = [
    re.compile(r"^(?:export\s+)?(?:default\s+)?(?:async\s+)?"
               r"(?:function|class)\s+([A-Za-z_]\w*)", re.M),
    re.compile(r"^(?:def|class)\s+([A-Za-z_]\w*)", re.M),
    re.compile(r"^(?:local\s+)?function\s+([A-Za-z_][\w.:]*)", re.M),
    re.compile(r"^([a-z_]\w*)\s*\(\)\s*\{", re.M | re.I),
    re.compile(r"^(?:pub\s+)?(?:async\s+)?fn\s+([A-Za-z_]\w*)", re.M),
    re.compile(r"^func\s+(?:\([^)]*\)\s*)?([A-Za-z_]\w*)", re.M),
    re.compile(r"^(?:export\s+)?const\s+([A-Za-z_]\w*)\s*=\s*(?:async\s*)?\(", re.M),
    re.compile(r"^([A-Z][A-Z0-9_]{3,})\s*=", re.M),
    # `pub(?:\([^)]*\))?` covers Rust's `pub type X = …` and `pub(crate) type X = …`;
    # bare `type X = …` (no modifier) still matches for Go's `type Foo struct {`.
    re.compile(r"^(?:export\s+)?(?:declare\s+)?(?:abstract\s+)?"
               r"(?:pub(?:\([^)]*\))?\s+)?"
               r"(?:interface|type)\s+([A-Za-z_$][\w$]*)", re.M),
    # `enum` is split off from the two above because it is the one of the three
    # that C also writes at a use site — `enum reset_state state;` — so it needs
    # the same guard as _DECL_TYPE below. TypeScript's `enum Color {` and a bare
    # `enum mode;` both still match; only a following identifier rejects.
    re.compile(r"^(?:export\s+)?(?:declare\s+)?(?:abstract\s+)?"
               r"enum\s+([A-Za-z_$][\w$]*)(?![\w$])(?![ \t]+[A-Za-z_$*])", re.M),
    # `final`/`val` join const/let/var: Dart declares most top-level state as
    # `final fooProvider = …`, which was 80 of 165 missed symbols on a Flutter
    # app. Anchored at column 0, so Java's indented `final` fields stay out.
    re.compile(r"^(?:export\s+)?(?:const|let|var|final|val)\s+"
               r"([A-Za-z_$][\w$]*)\s*[:=]", re.M),
    # Typed top-level binding with no initialiser on the name line:
    #   var globalContext homeContext        (Go)
    #   const ErrNoHostsPaths errors.Error = "…"
    # The [:=] pattern above misses these because a type sits between the name
    # and the `=`, or there is no `=` at all.
    #
    # The trailing `(?://[^\n]*)?` tolerates a same-line `//` comment after the
    # type, bounded to the rest of that one line only (never `\s*`, which
    # could cross into a later line the way `_TYPE` above warns against).
    # Without it this pattern missed every exported Go var/const documented
    # with a trailing comment -- idiomatic per `golint` -- since `$` cannot
    # match with comment text still between it and true end of line.
    # Confirmed on the standard library: `var testOut *strings.Builder //
    # Gathers output when testing.` in cmd/asm went uncaptured until this.
    re.compile(r"^(?:export\s+)?(?:const|var|final|val)\s+([A-Za-z_]\w*)\s+"
               r"[A-Za-z_\[\*][\w\.\[\]\*]*\??\s*(?:=|(?://[^\n]*)?$)", re.M),
    # The same two tokens in the opposite order: Go writes `const Name Type =`,
    # but Dart/C/Java write `const Type name =`. Both are `const A B =`, so the
    # only way to tell them apart is the type — this fires solely on a known
    # primitive in first position, which leaves Go's form to the pattern above.
    re.compile(r"^(?:export\s+)?(?:static\s+)?(?:const|final|val)\s+"
               r"(?:bool|int|double|num|String|Object|char|float|long|short|"
               r"byte|dynamic|var)\??\s+([A-Za-z_$][\w$]*)\s*=", re.M),
    # Go groups declarations inside parens. These must stay narrow: a bare
    # `^\t(name) =` also matches every indented key in a Lua table, which once
    # took a repo's graph from 180 rows to 999.
    #
    # Deliberately does NOT tolerate a trailing `//` comment the way the
    # column-0 twin above does: this shape -- tab-indented `name Type`, no
    # `:`/`;` between them -- is identical to a Go struct field, and comments
    # are the common case for exported struct fields (idiomatic per golint),
    # not for bare grouped var/const entries. Adding the same `(?://...)?$`
    # tolerance here once made every documented struct field leak as a
    # top-level symbol (`type Config struct { Name string // ... }` yielded
    # `Config`, `Name`, `Port` instead of just `Config`) -- a much larger
    # false-positive class than the grouped-entry case it was meant to catch.
    #
    # The `(?!=)` is positional, and it is what keeps Lua's `\telseif a == b
    # then` out: `elseif` lands in the name slot, `a` in the type slot, and a
    # bare `=` was satisfied by the first half of `==`. Go's grouped
    # `\tMaxSize int = 10` is untouched — its `=` is followed by a space. The
    # other comparison and compound-assignment forms never reached this
    # pattern to begin with: after the type slot `\s*` needs a literal `=` and
    # finds `~`/`>`/`<`/`!`/`+`, so `~=`, `>=`, `+=` were already rejected.
    # Measured on a tab-indented Lua codebase this alone removed 42 matches.
    #
    # The `[ \t]` classes replace what were `\s`, and the bound is the same
    # one the column-0 twin above already documents: `\s` crosses newlines, so
    # between the name slot and the type slot this pattern would walk forward
    # into the *next* line hunting a second token. Lua's block keywords are
    # what exposed it — `\trepeat\n\t\tstillRunning = false` matched as though
    # `repeat` were a name and `stillRunning` its type. Go's grouped entries
    # are single-line by construction (`\tMaxSize int = 10`, `\tHost string`),
    # so bounding costs the intended shape nothing.
    re.compile(r"^\t([A-Za-z_]\w*)[ \t]+[A-Za-z_\[\*][\w\.\[\]\*]*"
               r"(?:[ \t]*=(?!=)|[ \t]*$)", re.M),
    re.compile(r"^\t([A-Za-z_]\w*)\s*=\s*iota\b", re.M),
    re.compile(r"^\t([A-Za-z_]\w*)\s+(?:struct|interface)\s*\{", re.M),
    # The same anonymous struct/interface type, standalone rather than inside
    # a `var (...)` group -- `var DebugFlags struct {...}` at column 0. Only
    # `var` takes this shape in Go; `const` cannot hold a composite literal
    # type. Confirmed missing on the standard library's
    # cmd/asm/internal/flags/flags.go, where `DebugFlags` itself went
    # uncaptured (its fields still surfaced, via the grouped-block pattern
    # above, as if the struct had no name at all).
    re.compile(r"^var\s+([A-Za-z_]\w*)\s+(?:struct|interface)\s*\{", re.M),
    re.compile(r"^\s*function\s+([A-Za-z_][\w-]*)", re.M | re.I),
    re.compile(r"^\s*(?:class|enum)\s+([A-Za-z_]\w*)\s*\{", re.M | re.I),
    re.compile(r"^\s*(?:class|struct|union|enum(?:\s+class)?)\s+([A-Za-z_]\w*)"
               r"\s*(?:final\s*)?(?::|\{)", re.M),
    # Both prefixes are bounded, and the bound is load-bearing. These classes
    # contain `\s`, so unbounded (`*?`) the engine walks forward from every line
    # start across newlines hunting for a `::` or a `(` that may not exist —
    # quadratic in file size, the same trap `_TYPE` above documents. It went
    # unnoticed until the Linux kernel: on its 36,517-line
    # `tools/testing/radix-tree/maple.c` (which contains zero `::`) the second
    # pattern took 24.4s on a 400KB slice and rose 4x per doubling, so the full
    # file never finished. Bounding the prefix to 80 chars caps the work per
    # line: 24.389s -> 0.039s on that slice, identical matches.
    #
    # Bound the PREFIX only. Bounding the parameter list too was measured and
    # rejected: it bought no speed at all (flat from 400 to 8000 chars) and cost
    # 11 real kernel symbols whose signatures run 422-525 chars —
    # `__vringh_iov`, `slow_copy`, `__libeth_xdp_run_flush`, `DEF_SCSI_QCMD`.
    # Diffed across all 17 cached repos, the prefix bound alone loses exactly
    # one name: `pipes`, matched inside an English comment via a 191-char
    # prefix. The other four it drops are the same kind — `ports`, `arch` from
    # help text and `files` from the MIT licence header.
    re.compile(r"^[A-Za-z_][\w:<>,\s\*&]{0,80}?\b[A-Za-z_]\w*::([A-Za-z_~]\w*)\s*\(", re.M),
    re.compile(r"^(?:static\s+|inline\s+|extern\s+|const\s+|virtual\s+)*"
               r"(?:[A-Za-z_][\w:<>,\*&\s]{0,80}?\s+[\*&]?)([A-Za-z_]\w*)\s*"
               r"\([^;{]*\)\s*(?:const\s*)?(?:noexcept\s*)?\{", re.M),
    re.compile(r"^\s*#\s*define\s+([A-Za-z_]\w*)", re.M),
    re.compile(r"^\s*typedef\s+.*?\b([A-Za-z_]\w*)\s*;", re.M),
    # QML declares a member as `property <type> <name>: …`. The keyword-led
    # generic pattern captures the *type* here, not the name, because QML puts
    # both between the keyword and the identifier — so without this, a Qt client
    # yielded 26% of its QML declarations and 81 of 140 files gave nothing.
    # `signal` is spelled out rather than folded into _DECL for the same reason,
    # and requiring whitespace after it leaves Qt C++'s `signals:` label alone.
    re.compile(r"^\s*(?:readonly\s+)?(?:default\s+)?property\s+"
               r"[\w<>\.]+\s+([A-Za-z_]\w*)", re.M),
    re.compile(r"^\s*signal\s+([A-Za-z_]\w*)", re.M),
]

# Generic layer: declaration *shapes*, not languages.
GENERIC = [
    # [modifiers] KEYWORD Name — the shape ~every language uses. The name class
    # allows hyphens and dots so `Get-WinUtilThing` and `Croc.Transfer` survive
    # whole rather than being truncated at the separator.
    #
    # The trailing lookaheads reject `impl Default for CommandRegistry {`,
    # where `impl` is in _DECL and the word right after it is the trait being
    # implemented, not a name this file declares — `Default` isn't declared
    # here, `CommandRegistry` (after `for`) already is, via its own `struct`.
    # Unguarded this pulled 3,255 external trait names into the cached Rust
    # corpus as if they belonged to the file that merely implements them —
    # `Default` alone 414 times. No _DECL keyword other than `impl` is ever
    # followed by `for` in real syntax, so the lookahead costs nothing there.
    # The optional `(?:<[^>\n]*>)?` before `for` is required, not cosmetic:
    # `impl From<u64> for JsCallbackId {` has a generic argument list between
    # the trait name and `for`, and without tolerating it here `From` still
    # read as declared — the single most common case, since every generic
    # trait impl (`From<T>`, `TryFrom<T>`, `PartialEq<T>`) takes this shape.
    # Bounded to one line, same reasoning as `_TYPE` above: unbounded, a file
    # with no `>` on the line would walk forward across newlines hunting one.
    #
    # The first lookahead is load-bearing, not decoration, same as the
    # _DECL_TYPE rule below: without it the greedy name class backtracks to
    # satisfy the second one, so `Default` shrinks to `Defaul` (whose next
    # character is `t`, not whitespace) instead of being rejected outright.
    re.compile(rf"^[ \t]{{0,16}}{_MOD}(?:{_DECL})\s+([A-Za-z_$][\w$.-]*)"
               r"(?![\w$.-])(?!(?:<[^>\n]*>)?\s+for\b)", re.M),
    # Same shape for the four type keywords, plus a guard that a declaration
    # satisfies and a use does not: what follows the name. `struct foo {`,
    # `struct foo;` and Rust's `struct Foo(u32);` are declarations; `struct
    # list_head list;` and `static struct platform_driver x = {` are uses, and
    # the giveaway is a second identifier (or a `*`) right after the type.
    #
    # The first lookahead is not decoration. Without it the greedy name class
    # backtracks to satisfy the second one — `list_head` would shorten to
    # `list_hea`, whose next character is `d` rather than whitespace — and the
    # pattern would emit truncated names instead of rejecting the line.
    #
    # C++'s `struct Foo final : Bar {` is rejected here (a second identifier
    # follows) and is deliberately left to the SPECIFIC rule above, which spells
    # out `final` and so keeps it.
    re.compile(rf"^[ \t]{{0,16}}{_MOD}(?:{_DECL_TYPE})\s+([A-Za-z_$][\w$.-]*)"
               r"(?![\w$.-])(?![ \t]+[A-Za-z_$*])", re.M),
    # name = function / <- function / := func / = (args) =>
    #
    # Known, deliberate gap, confirmed against a tree-sitter AST rather than
    # left as a guess: Svelte 5's entire reactivity model is a plain
    # top-level `let x = $state(...)` / `let y = $derived(...)`, whose RHS is
    # an ordinary function call, not one of the shapes required above -- so
    # none of it is captured. `tests/ts_oracle.py --lang svelte`, scoped to
    # the files build_graph.py actually enumerates (real component files, not
    # the thousands of per-test-case fixtures under samples/, which collapse
    # to one row and were never in scope), found 48 such misses across 44
    # files, 100% of them this one class -- no other gap behind it. Left
    # unfixed: every widening in this file's history has nearly broken
    # something else (Dart's `=>`-body support alone added 882 false names
    # on this same svelte repo, see that pattern's comment below), and a
    # bare `name = <anything>` shape is far riskier than that one was, since
    # it would have no distinguishing RHS at all to guard it.
    re.compile(r"^[ \t]{0,8}(?:(?:export|local|pub|const|let|var|val|my|our)\s+)?"
               r"([A-Za-z_$][\w$]*)\s*(?:=|<-|:=)\s*"
               r"(?:function|func|fn|proc|lambda|async|\([^)]*\)\s*(?:=>|->|\{))", re.M),
    # [modifiers] [type] name(args) { — C-family, Java, C#, Swift, Dart, Groovy
    # The type may now be nullable (`ReadStateBlob? decode(…) {`), but `{` stays
    # banned inside the params. Allowing it here let `export default test({` run
    # on to the next line and swallow the `snapshot(target) {` under it, costing
    # 467 files a real symbol. Signatures that need `{` in their params go to
    # the typed pattern below, which cannot start on a bare call.
    re.compile(rf"^[ \t]{{0,16}}{_MOD}(?:{_TYPE}\s+[\*&]?)?"
               r"([A-Za-z_$][\w$]*)\s*\([^;{)]*\)\s*"
               r"(?:const\s*|noexcept\s*|throws\s[\w,\s]+|->\s*[\w<>\[\], ]+\s*"
               r"|:\s*[\w<>\[\], ]+\s*)*\{", re.M),
    # Same shape with a REQUIRED return type, which buys three things the form
    # above cannot have safely: `{` in the params (Dart named args,
    # `fmt(int s, {DateTime? now}) {`), a trailing `async`, and an expression
    # body (`String keyFor(String p) => …;`).
    #
    # The mandatory type is what makes those safe. Without it this shape is
    # indistinguishable from a call whose last argument is a closure —
    # `setTimeout(() => {`, `describe('x', () => {`, `testWidgets('x', (t) async {`
    # — which added 882 such names on svelte and 876 on buzz, all call sites.
    # The lookahead then drops `return new Promise((r) => {`, where `return new`
    # would otherwise read as the type, and the lookbehind stops a type ending
    # in `:` or `,`, which is how a Flutter widget argument — `leading:
    # TextButton(` — passed `leading:` off as a return type. `::` is unaffected,
    # so C++ `std::string parse(…) {` still matches.
    re.compile(rf"^[ \t]{{0,16}}{_MOD}"
               r"(?!(?:return|await|throw|yield|new|delete|typeof|case|else)\b)"
               rf"{_TYPE}(?<![:,])\s+[\*&]?"
               r"([A-Za-z_$][\w$]*)\s*\((?:[^;()]|\([^()]*\))*\)\s*"
               r"(?:async\s*)?(?:=>|\{)", re.M),
    # Haskell-style top-level type signature
    re.compile(r"^([a-z_][\w']*)\s*::", re.M),
    # SQL DDL
    re.compile(r"\bCREATE\s+(?:OR\s+REPLACE\s+)?(?:UNIQUE\s+)?"
               r"(?:TABLE|VIEW|INDEX|FUNCTION|PROCEDURE|TRIGGER|MATERIALIZED\s+VIEW)\s+"
               r"(?:IF\s+NOT\s+EXISTS\s+)?[`\"\[]?([A-Za-z_]\w*)", re.M | re.I),
    # HCL / Terraform blocks
    re.compile(r'^(?:resource|variable|output|module|provider|data)\s+"([^"]+)"', re.M),
    # Objective-C
    re.compile(r"^@(?:interface|implementation|protocol)\s+([A-Za-z_]\w*)", re.M),
    re.compile(r"^[-+]\s*\([^)]*\)\s*([A-Za-z_]\w*)", re.M),
    # Component metadata in object literals (Vue, some JS frameworks). Vue's
    # own style guide has the value PascalCase, which is also what separates
    # a real component name from the same `name: "value",` shape written by
    # every other struct/dict literal that happens to have a `name` field —
    # Go's table-driven tests (`{name: "invalid_cookie", ...}`) and Rust's
    # generated data tables (`Block { name: "cobblestone_stairs", ... }`)
    # both use it constantly, and neither is a declaration. Unrestricted, this
    # pulled 1,265 lowercase data values into the graph as symbols across 15
    # generated files in the cached corpus; requiring an uppercase first
    # letter cut that to 8 residual (capitalised test-fixture values, e.g.
    # `name: "Alice"`) while keeping the Vue fixture's `TransferPanel`.
    re.compile(r"^\s{0,8}name:\s*['\"]([A-Z][\w$]*)['\"]", re.M),
    # Method shorthand inside classes / object literals
    re.compile(r"^[ \t]{2,16}([A-Za-z_$][\w$]*)\s*\([^;{)]*\)\s*\{", re.M),
    # SCREAMING_CASE constants. `pub(?:\([^)]*\))?` rather than bare `pub` so
    # Rust's scoped visibility — `pub(crate) const X`, `pub(super) const Y` —
    # matches the same as plain `pub const X`; this was the only shape the
    # bare form missed on the eleven `pub(crate|super) const` items in a
    # 989-file Rust repo.
    re.compile(r"^[ \t]{0,4}(?:(?:export|pub(?:\([^)]*\))?|const|final|static|"
               r"readonly|val|var|let)\s+)*"
               r"([A-Z][A-Z0-9_]{2,})\s*(?::[^=]+)?[=:]", re.M),
    # The same constant with a type in front and an access modifier on it —
    # `private static final int PING_INTERVAL = …`. Java and C# write every
    # constant this way, and the pattern above matches none of them: its
    # modifier list has no `public`/`private`, and it leaves no room for the
    # type sitting between the modifiers and the name. This was 1,049 of the
    # 1,822 declarations missed on Jenkins, the single largest class there.
    #
    # At least one modifier is required, which is what keeps `case FOO_BAR:`
    # out — a switch label would otherwise read as a type followed by a name.
    re.compile(r"^[ \t]{0,16}(?:(?:public|private|protected|internal|static|"
               r"final|const|readonly|volatile|transient|abstract)\s+)+"
               r"(?:[A-Za-z_][\w<>\[\],\.\s]*?\s+)?([A-Z][A-Z0-9_]{2,})\s*=", re.M),
    # Protocol Buffers' two top-level keywords. Both require a same-line `{`,
    # unlike every other keyword-led shape above: "message" and "service" are
    # ordinary English words, and `service NAME stop` is the standard sysadmin
    # shell idiom, not a declaration. Folding them into the bare keyword-led
    # GENERIC pattern (no brace requirement) caught both — comment prose
    # ("service must be installed before it can be run...") and that shell
    # idiom — on amnezia-client and pi-hole, neither of which has a single
    # .proto file. Requiring the brace costs nothing: proto never splits a
    # message/service name from its opening `{` across lines.
    re.compile(r"^[ \t]{0,16}(?:message|service)\s+([A-Za-z_]\w*)\s*\{", re.M),
]

KEYWORDS = {
    # Control flow — matches the parenthesised-signature shape.
    "if", "for", "while", "switch", "return", "sizeof", "else", "do", "catch",
    "throw", "case", "defined", "static_cast", "and", "not",
    "operator", "template", "typename", "elif", "unless", "until", "foreach",
    "when", "match", "with", "try", "finally", "select", "defer", "go",
    # Declaration keywords: one language's keyword landing in another's syntax
    # captured these as names.
    "var", "const", "let", "type", "func", "function", "class", "enum",
    "interface", "struct", "package", "import", "export", "async",
    "await", "static", "public", "private", "protected", "abstract", "final",
    "impl", "trait", "module", "namespace", "record", "object", "def", "end",
    "use", "require", "include", "extends", "implements", "returns", "local",
    # `local` belongs in this bucket for the same reason `end` already does:
    # it is Lua's declaration keyword landing in Go's grouped-declaration
    # syntax. `\tlocal x = 1` is shape-identical to `\tMaxSize int = 10`, and
    # no positional guard separates them — the keyword sits in the very slot
    # the pattern captures, so the discriminator is lexical or nothing.
    # Measured on a tab-indented Lua codebase this was 148 matches, the
    # single largest false-positive class in that graph.
    #
    # This is not the `new`/`delete`/`default`/`from` mistake reverted below.
    # Those were reverted because each is a high-frequency *declared* name in
    # some language — `fn new()` in 1,120 of 3,933 cached Rust files — so
    # blocking by name cost real symbols. `local` is not in that class:
    # re-running the pre-fix extractor over croc (48 Go files) and ripgrep
    # (110 Rust files) captured a symbol named `local` in 0 of 158, so this
    # entry costs those languages nothing it was protecting.
    # `default`/`from` used to sit here too, the same blanket-blocklist
    # mistake `new`/`delete` made: no pattern in SPECIFIC or GENERIC ever
    # captures either from a switch's `default:` label, JS's `export
    # default`, or Python/JS's `from`-import — `default` is already consumed
    # as a modifier by `_MOD` wherever it's a real re-export, and none of the
    # import shapes resemble a declaration to begin with. Blocking them by
    # name alone cost Rust's two most-implemented traits: `fn default()` and
    # `fn from()`, dropped from 346 and 84 files respectively in the cached
    # corpus. No positional guard was needed — unlike `new`/`delete`, nothing
    # real was ever found to protect.
}

# A name the pattern had to stop short of finishing, because the character after
# it cannot be part of an identifier but the name plainly continues: `Get` cut
# out of `Get-WinUtilThing`, or `idx_` out of a SQL string a shell script
# interpolates into, `CREATE INDEX idx_${table}`. Never a real symbol — the
# whole name is, where there is one, and the keyword-led rule above captures it.
#
# The interpolation half is not hypothetical tidiness. That `idx_` is a name no
# file in pi-hole contains, and the verifier refused the graph the generator had
# just written for it — a false block on every refresh. It is the only such
# match across the seventeen cached repos, so the guard costs nothing.
#
# This was a blocklist of the seventeen PowerShell verbs instead, matched
# against the name alone. But the defect is positional, not lexical: a stranded
# verb is always followed by `-` and an identifier, and a real declaration never
# is. Judging by name discarded every genuine `Add`/`Get`/`Start`/`read` in any
# language — 4,048 of the 4,208 blocked matches across the cached repos, 96%,
# against 160 true fragments. It cost shell its `stop() {` and `start() {`
# outright, and Go every `func (w *OSWatcher) Start(` it declares.
#
# Anchoring on the following character keeps all 160 out and gives the rest
# back. The trailing `[A-Za-z_]` is what separates the compound name from an
# arithmetic `-`, which no declaration pattern can be followed by anyway.
_TRUNCATED = re.compile(r"-[A-Za-z_]|\$[\w{]")

# `new`/`delete` used to sit in KEYWORDS as a blanket blocklist, the same
# mistake the PowerShell verb list above made: the defect that motivates it —
# C++'s `void* operator new(size_t) {` reading as a declaration of `new` — is
# positional, not lexical, and judging by name discarded `fn new()` from 1,120
# of 3,933 Rust files across the cached corpus (28%), the single most common
# constructor name in the language. Only `operator new`/`operator delete`
# needs rejecting; anchoring on the preceding token gives every other `new`
# and `delete` back, in any language.
_OPERATOR_KEYWORD = re.compile(r"\boperator\s+$")


def _strip_python_strings(text):
    """Blank the content of every Python string/docstring token.

    A documentation-heavy module's docstring routinely shows a usage example
    — `\"\"\"\n@app.get(\"/\")\ndef create_item(item: Item):\n    ...\n\"\"\"` — and the
    keyword-led GENERIC pattern cannot tell that from real code: `def` at
    column 0 inside a docstring reads exactly like `def` at column 0 outside
    one. Confirmed on fastapi: `applications.py` alone contributed 12 fake
    declarations this way (`create_item`, `delete_item`, `websocket_endpoint`,
    `Item`, …), and the same fake names repeating across multiple files'
    example docstrings is a plausible explanation for fastapi being the
    corpus's 1-file-localization outlier (75.2% against 85-98% elsewhere).

    Uses `tokenize` — the same lexer CPython itself uses — rather than a
    regex that pairs up `\"\"\"`/`'''` occurrences by counting them. Counting
    is not enough to be safe: two unrelated stray triple-quote sequences
    inside two different ordinary strings can sum to an even count while
    pairing with *each other* instead of each canceling within its own
    string, silently blanking every real declaration in between. A real
    tokenizer has no such failure mode — it already knows where each string
    starts and ends.

    Fails safe: `tokenize` raises on input it cannot parse (a deliberately
    incomplete fixture snippet, a real syntax error); any exception returns
    `text` unchanged rather than risk doing something worse than nothing.

    `FSTRING_MIDDLE` (PEP 701, Python 3.12+) is checked alongside `STRING`:
    from that version on, an f-string tokenizes as START/MIDDLE/END parts
    rather than one opaque STRING token, and skipping it let fake code
    inside an f-string docstring (`f\"\"\"...\ndef fake(): ...\n\"\"\"`) leak
    through untouched. `getattr` degrades to a no-op check on older Python,
    where f-strings are already plain STRING tokens.
    """
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(text).readline))
    except Exception:
        return text
    fstring_middle = getattr(tokenize, "FSTRING_MIDDLE", None)
    lines = text.split("\n")
    for tok in tokens:
        if tok.type != tokenize.STRING and tok.type != fstring_middle:
            continue
        (srow, scol), (erow, ecol) = tok.start, tok.end
        if srow == erow:
            line = lines[srow - 1]
            lines[srow - 1] = line[:scol] + " " * (ecol - scol) + line[ecol:]
        else:
            lines[srow - 1] = lines[srow - 1][:scol]
            for row in range(srow, erow - 1):
                lines[row] = ""
            lines[erow - 1] = " " * ecol + lines[erow - 1][ecol:]
    return "\n".join(lines)


_GO_SPECIAL = re.compile(r"[/\"'`]")


def _strip_go_raw_strings(text):
    """Blank the content of every Go raw string literal (backtick-quoted).

    A Go raw string is the one construct in this language that can span
    multiple lines, so an embedded CLI usage block or shell-script template
    reads exactly like real column-0 declarations to every keyword-led
    pattern in this file. Confirmed on cobra: `bash_completions.go` embeds a
    generated bash script inside a raw string, and its `COMPREPLY=()` line
    matched the SCREAMING_CASE constant pattern until this stripped it; the
    Go standard library's `scriptreadme_test.go` does the same with a
    `GOARCH=<target GOARCH>` style env-var doc block.

    A blind `` `[^`]*` `` regex is not safe here, even though a raw string
    itself cannot contain a backtick: a stray backtick anywhere *else* in the
    file — inside a regular string (`strings.Trim(s, "`")`), a rune literal
    (`'`'`), or a comment — pairs with the next real backtick instead of its
    actual partner, which desyncs every raw string after it: the declaration
    the mispaired span blanks is lost, and the real raw-string content past
    it goes completely unstripped. So this walks the text once, skipping
    line comments, block comments, regular strings and rune literals
    verbatim — the only constructs whose own quoting can contain a backtick —
    and only treats a backtick as a raw-string delimiter when none of those
    are open. `_GO_SPECIAL` lets each plain-code run between one `/`, `"`,
    `'` or backtick and the next be sliced out in one C-level step, so this
    stays linear rather than looping per character.
    """
    out = []
    i, n = 0, len(text)
    while i < n:
        m = _GO_SPECIAL.search(text, i)
        if m is None:
            out.append(text[i:])
            break
        j = m.start()
        out.append(text[i:j])
        c = text[j]
        if c == "/" and j + 1 < n and text[j + 1] == "/":
            k = text.find("\n", j)
            k = n if k == -1 else k
            out.append(text[j:k])
            i = k
        elif c == "/" and j + 1 < n and text[j + 1] == "*":
            k = text.find("*/", j + 2)
            k = n if k == -1 else k + 2
            out.append(text[j:k])
            i = k
        elif c == "/":
            out.append(c)
            i = j + 1
        elif c in ("\"", "'"):
            # A newline bails out of an unterminated literal instead of
            # scanning past it, since Go's interpreted strings and rune
            # literals can never contain a real one anyway.
            k = j + 1
            while k < n and text[k] != c and text[k] != "\n":
                k += 2 if text[k] == "\\" else 1
            k = min(k + 1, n)
            out.append(text[j:k])
            i = k
        else:  # backtick
            k = text.find("`", j + 1)
            if k == -1:
                out.append(text[j:])
                i = n
                break
            out.append("`" + re.sub(r"[^\n]", " ", text[j + 1:k]) + "`")
            i = k + 1
    return "".join(out)


def _is_keyword(name):
    """True if `name` is a language keyword rather than an identifier.

    Case matters. Keywords are lowercase in every language here, so an
    exact-case match rejects `package`/`match`/`type` while leaving `Package`
    (a real Go constant) and `Match` (a real method) alone. Matching
    case-insensitively cost two real symbols on a Go repo; the only language
    that would need otherwise is one with case-insensitive keywords, and there
    the capitalised form is vanishingly rare as a declared name.
    """
    return name in KEYWORDS


def extract(text, generic=True, ext=None):
    """Ordered, de-duplicated symbol names declared in `text`.

    `ext`, when given as `.py`, strips string/docstring content first — see
    `_strip_python_strings`. `.go` strips raw string literals the same way —
    see `_strip_go_raw_strings`. Optional and defaulted to `None` so every
    existing caller (including every fixture in test_symbols.py, none of
    which names a real file) keeps behaving exactly as before.
    """
    if ext == ".py":
        text = _strip_python_strings(text)
    elif ext == ".go":
        text = _strip_go_raw_strings(text)
    found, seen = [], set()
    layers = SPECIFIC + GENERIC if generic else SPECIFIC
    for rx in layers:
        for m in rx.finditer(text):
            name = m.group(1)
            if not name or len(name) < 3 or name in seen:
                continue
            if _is_keyword(name) or _TRUNCATED.match(text, m.end(1)):
                continue
            if name in ("new", "delete") and _OPERATOR_KEYWORD.search(
                    text, max(0, m.start(1) - 16), m.start(1)):
                continue
            seen.add(name)
            found.append(name)
    return found
