#!/usr/bin/env python3
"""Conformance suite for symbol extraction. Run before trusting a change.

    python3 tests/test_symbols.py

Two halves, both of which have caught real regressions:

RECALL  — 22 language fixtures nobody wrote a specific rule for. This is the
          guard against the pattern that made every earlier held-out benchmark
          fail: the extractor working only on languages it had already met.
          Per-language patterns alone score 26% here; with the generic layer,
          96%. The gate is set below the current score so an ordinary drop
          fails the build rather than passing quietly.

PRECISION — cases that produced observed false positives: a PowerShell verb
          stranded from its noun, a Go package name, a Lua data table read as
          declarations, control-flow keywords matching the C function shape.

Exits non-zero on failure. Stdlib only.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                                "scripts"))
from lib_symbols import extract  # noqa: E402
from lib_extensions import CODE_EXT  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES = os.path.join(HERE, "fixtures")

# fixture -> symbols a reader would search for in it
EXPECTED = {
    "rust.rs": ["connect_peer", "RelayConfig", "TransferState", "Encoder", "MAX_RETRIES",
                "HookCallback", "MAX_QUEUE", "RETRY_DELAY_MS"],
    "java.java": ["TransferManager", "startTransfer", "getInstance", "PeerListener", "Phase",
                  "PING_INTERVAL", "LOGGER", "HEADER_DEFAULTS", "close",
                  "beforeRequest", "afterResponse", "register"],
    "qml.qml": ["contentHeight", "isFocusable", "serverName", "contentData",
                "configPrepared", "reloadServers"],
    "csharp.cs": ["RelayServer", "Start", "ComputeHash", "IPeer", "Point", "Mode"],
    "ruby.rb": ["Croc", "Transfer", "send_file"],
    "php.php": ["FileTransfer", "send", "hashOf", "Encoder", "Loggable", "helper_format"],
    "swift.swift": ["PeerConnection", "connect", "shared", "TransferOptions", "State",
                    "Encodable2", "globalHelper"],
    "kotlin.kt": ["RelayClient", "connect", "Listener", "Config", "topLevelHelper", "Registry"],
    "scala.scala": ["Transfer", "send", "apply", "Encoder", "Options"],
    "elixir.ex": ["Croc.Transfer", "send_file", "validate", "guard_valid"],
    "perl.pl": ["Transfer", "send_file"],
    "r.r": ["compute_score", "normalize_data"],
    "julia.jl": ["Transfer", "send_file", "Options", "MAX_SIZE"],
    "dart.dart": ["PeerConnection", "connect", "create", "Encoder", "State", "globalHelper",
                  "activityProvider", "mockDmDirectoryEnabled", "customEmojiSetDTag",
                  "decodeReadStateBlob", "threadContextKey", "refreshChannels",
                  "showEmojiPicker", "processCapturedImage", "AppThemeExtension"],
    "haskell.hs": ["sendFile", "TransferState", "Port", "Encoder"],
    "zig.zig": ["connectPeer", "internalHelper"],
    # Derived from `ts_oracle.py --lang lua`, not read off the fixture. The
    # oracle also reports `M`, which extract() drops via its global
    # 3-character floor -- deliberate and language-independent, so it is not
    # listed here as a symbol the extractor owes.
    "lua.lua": ["computeHash", "localizeName", "M.connectPeer", "M:closeAll",
                "formatLine"],
    "terraform.tf": ["aws_instance", "region", "network", "relay_ip"],
    "sql.sql": ["transfers", "idx_transfers_id", "active_transfers", "compute_hash"],
    "vue.vue": ["TransferPanel", "sendFile"],
    "objc.m": ["PeerConnection", "connectToHost", "shared"],
    "groovy.groovy": ["BuildRunner", "execute", "create", "topLevelHelper", "Hook"],
    "shell.sh": ["start", "stop", "ensure_basic_configuration", "validate_env",
                 "CONFIG_PATH", "FTL_EXIT_CODE"],
    "proto.proto": ["Status", "STATUS_UNSPECIFIED", "STATUS_ACTIVE",
                    "GetForecastRequest", "ForecastService"],
}

RECALL_GATE = 0.90

# (label, source, must_contain, must_not_contain)
PRECISION = [
    ("powershell verb is not a symbol",
     "function Get-WinUtilVariable {\n}\nfunction Add-SelectedApp {\n}\n",
     ["Get-WinUtilVariable", "Add-SelectedApp"], ["Get", "Add"]),
    # The case above was enforced by a blocklist of seventeen verb spellings, so
    # any verb outside it leaked its truncation through: winutil emitted `Close`,
    # `Install`, `Find`, `Reset` and `Save` as symbols alongside the real names.
    # The rule is positional now, so the verb spelling no longer matters.
    ("an unlisted powershell verb is truncated too",
     "function Close-WinUtilRunspacePool {\n}\nfunction Save-WinUtilFile {\n}\n",
     ["Close-WinUtilRunspacePool", "Save-WinUtilFile"], ["Close", "Save"]),
    # A shell script building SQL by interpolation. The DDL rule runs on every
    # file, so it captured `idx_` and stopped at the `$` — a name no file in the
    # repo contains, which made the verifier reject the graph the generator had
    # just produced for pi-hole.
    ("a name truncated at an interpolation is not a symbol",
     'output=$(sqlite3 "$db" "CREATE INDEX idx_${table} ON ${table} (domain);")\n'
     'CREATE TABLE adlist (id INTEGER);\n',
     ["adlist"], ["idx_", "idx"]),
    # The other side of that fix, and the reason it could not stay a blocklist.
    # `stop() {` is how shell spells a declaration, and the blocklist dropped it
    # outright — one of docker-pi-hole's sixteen symbols, and the whole of its
    # coverage gap.
    ("a shell function named for a bare verb is a symbol",
     "start() {\n    echo up\n}\n\nstop() {\n    echo down\n}\n",
     ["start", "stop"], []),
    # Same blocklist, same cost, in a language with receivers: every Go method
    # spelled with a bare verb was discarded before this.
    ("a go method named for a bare verb is a symbol",
     "func (w *OSWatcher) Start(ctx context.Context) (err error) {\n}\n"
     "func (w *OSWatcher) Add(name string) (err error) {\n}\n",
     ["Start", "Add"], []),
    ("go package name is not a symbol",
     'package croc\n\nimport (\n\t"fmt"\n)\n\nfunc Send() {}\n',
     ["Send"], ["croc", "fmt"]),
    ("lua data table is not declarations",
     'return {\n\tname = "Axe",\n\tlevel = 12,\n\ttags = { "weapon" },\n}\n',
     [], ["name", "level", "tags"]),
    # Tab-indented Lua statements land in the Go grouped-declaration shape
    # `^\t(name) Type =`. On a real tab-indented Lua codebase this was the
    # two largest false-positive classes in the graph: `local` 148 matches,
    # `elseif` 42. `local` is rejected lexically (it is in KEYWORDS beside
    # `end`); `elseif` positionally, by requiring the `=` not to be `==`.
    ("tab-indented lua statements are not declarations",
     "function build(env)\n\tlocal total = 0\n\tlocal cache = {}\n"
     "\tif env == nil then\n\t\ttotal = 1\n\telseif env >= 2 then\n"
     "\t\ttotal = 2\n\tend\n\treturn total\nend\n",
     ["build"], ["local", "elseif"]),
    # The near-miss beside it, same reasoning as shell's `stop() {`: a real
    # declaration whose name merely begins with a blocked keyword must
    # survive. Rewriting the `local` guard as a prefix match kills this.
    ("a lua name that starts with a keyword is a symbol",
     "local function localizeName(key)\n\treturn key\nend\n"
     "local function endpointFor(id)\n\treturn id\nend\n",
     ["localizeName", "endpointFor"], []),
    # The Go shape the `(?!=)` guard must not disturb: a grouped `var (...)`
    # block whose entries carry a type and an initialiser.
    ("go grouped var with type and value still works",
     "var (\n\tMaxSize int = 10\n\tRetryDelay time.Duration = 5\n"
     "\tDefaultHost string\n)\n",
     ["MaxSize", "RetryDelay", "DefaultHost"], []),
    # A lone tab-indented keyword with nothing after it on its line. `\s+` in
    # the same pattern crossed the newline and read the next line's first
    # token as the type, so `repeat` matched as a name -- the cross-line walk
    # this file's other patterns are already bounded against.
    ("a tab-indented block keyword does not consume the next line",
     "function loop()\n\trepeat\n\t\tstillRunning = false\n\tuntil done\nend\n",
     ["loop"], ["repeat", "until"]),
    ("control flow is not a symbol",
     "void render() {\n}\nif (ready) {\n}\nwhile (running) {\n}\nswitch (mode) {\n}\n",
     ["render"], ["if", "while", "switch"]),
    ("python still works",
     "def compute_hash(x):\n    pass\n\nclass Transfer:\n    def send(self):\n        pass\n",
     ["compute_hash", "Transfer", "send"], []),
    ("go still works",
     "func NewConnection(a string) *Comm {\n}\ntype Comm struct {\n}\n"
     "func (c *Comm) Close() {\n}\n",
     ["NewConnection", "Comm", "Close"], []),
    # Typed top-level bindings: a type sits between the name and `=`, or there
    # is no `=` at all. Both forms were missed on a 4,229-symbol Go repo.
    ("go typed const and var",
     'const ErrNoHostsPaths errors.Error = "no valid paths"\n'
     "var globalContext homeContext\n"
     "const LastSchemaVersion uint = 29\n",
     ["ErrNoHostsPaths", "globalContext", "LastSchemaVersion"], []),
    # The verifier's presence test used \b, which does not match before a
    # leading $ -- every $-prefixed symbol read as deleted (Svelte, jQuery, PHP).
    ("dollar-prefixed names survive extraction",
     "export function $destroy() {}\nexport function $on() {}\n",
     ["$destroy", "$on"], []),
    # Keyword matching is case-sensitive: keywords are lowercase everywhere, so
    # `Package` (a real Go const) and `Match` (a real method) must survive while
    # the lowercase forms stay rejected. Case-insensitive matching cost both.
    ("capitalised keywords are real identifiers",
     'const Package = "github.com/goccy/go-json"\n'
     "func (g *RouterGroup) Match(m []string) IRoutes {\n}\n",
     ["Package", "Match"], []),
    ("c++ still works",
     "class r_renderer_c : public r_IRenderer {\n};\n"
     "void r_renderer_c::Init() {\n}\n#define MAX_LAYERS 32\n",
     ["r_renderer_c", "Init", "MAX_LAYERS"], []),
    # Supporting Dart's expression bodies and trailing `async` means matching
    # `name(args) =>` and `name(args) async {`, which is exactly the shape of a
    # call whose last argument is a closure. Requiring a return type is what
    # separates them; without it these added 882 names on svelte and 876 on buzz.
    ("a call taking a closure is not a declaration",
     "setTimeout(() => {\n});\n"
     "describe('suite', () => {\n});\n"
     "testWidgets('renders', (tester) async {\n});\n"
     "  return new Promise((resolve) => {\n  });\n",
     [], ["setTimeout", "describe", "testWidgets", "Promise", "resolve"]),
    # A Flutter widget argument reads as `type name(` unless the type is barred
    # from ending in `:` — `leading:` was passing itself off as a return type.
    ("a widget argument is not a declaration",
     "Widget build(BuildContext context) {\n"
     "  return FrostedAppBar(\n"
     "    leading: TextButton(\n"
     "      onPressed: () => Navigator.of(context).pop(),\n"
     "    ),\n"
     "  );\n"
     "}\n",
     ["build"], ["TextButton", "Navigator", "onPressed", "leading"]),
    # Allowing `{` inside the untyped signature form let `test({` run past the
    # newline and swallow the method under it, silently costing 467 files a
    # symbol. Both names must survive.
    # Java constants need modifiers + a type before the name, but requiring at
    # least one modifier is what keeps a switch label out: with the modifier
    # group optional, `case FOO_BAR:` reads as a type followed by a name.
    ("a switch label is not a constant declaration",
     "        switch (mode) {\n"
     "        case FOO_BAR:\n"
     "        case BAZ_QUX:\n"
     "            SOME_VAR = compute();\n"
     "        }\n",
     [], ["FOO_BAR", "BAZ_QUX", "switch", "case"]),
    # Qt C++ spells its access label `signals:` with no name after it; the QML
    # `signal` pattern must require whitespace so the label never matches.
    ("a qt signals label is not a symbol",
     "class Foo : public QObject {\n"
     "signals:\n"
     "    void changed();\n"
     "};\n",
     ["Foo"], ["signals", "signal"]),
    # `struct X y;` uses a type, it does not declare one. Folded in with the
    # other declaration keywords this emitted the type name in every file that
    # mentioned it — `device` in 8,565 Linux kernel files, `platform_driver` in
    # 5,611 — which held 1-file localization to 47.8% against a 95.4% ceiling.
    # The declarations below must survive; only the uses are rejected.
    ("a c type use is not a declaration",
     "struct list_head list;\n"
     "static struct platform_driver foo_driver = {\n"
     "};\n"
     "typedef int u32;\n"
     "enum reset_state state;\n"
     "struct spi_device *spi;\n",
     ["u32"], ["list_head", "platform_driver", "reset_state", "spi_device"]),
    # The near-miss the guard could break: these ARE declarations, and each has
    # something after the name that must not be read as a second identifier.
    ("a type declaration still is one",
     "struct foo {\n"
     "\tint x;\n"
     "};\n"
     "union payload {\n"
     "};\n"
     "enum mode {\n"
     "};\n"
     "struct forward_decl;\n",
     ["foo", "payload", "mode", "forward_decl"], []),
    # `extends`/`final` put a real identifier straight after the declared name,
    # which is exactly the shape the guard rejects. Both must still resolve —
    # the C++ one via the SPECIFIC rule that spells out `final`.
    ("a declared name followed by a keyword survives",
     "class Session extends BaseSession {\n"
     "}\n"
     "struct Renderer final : IRenderer {\n"
     "};\n"
     "pub struct Config;\n"
     "pub struct Wrapper(u32);\n",
     ["Session", "Renderer", "Config", "Wrapper"], []),
    # The unbounded `\s`-bearing prefix in the C-family patterns matched across
    # dozens of lines of prose, so a licence header declared `files` and help
    # text declared `ports`. Bounding the prefix fixed it; these are the four
    # names it actually removed across the benchmark corpus.
    ("prose is not a declaration",
     "/*\n"
     " * Permission is hereby granted, free of charge, to any person obtaining\n"
     " * a copy of this software and associated documentation files (the\n"
     " * \"Software\"), to deal in the Software without restriction, including\n"
     " * without limitation the rights to use, copy, modify, merge, publish\n"
     " */\n"
     "int real_function(void)\n"
     "{\n"
     "\treturn 0;\n"
     "}\n",
     ["real_function"], ["files", "Software", "charge"]),
    ("a call passing an object literal does not swallow the method below it",
     "import { test } from '../../test';\n\n"
     "export default test({\n"
     "\tsnapshot(target) {\n"
     "\t\treturn target.querySelector('h1');\n"
     "\t}\n"
     "});\n",
     ["snapshot"], []),
    # `message`/`service` are ordinary English words, and `service NAME verb` is
    # the standard sysadmin shell idiom — not a proto declaration. Folding them
    # into the bare keyword-led GENERIC pattern (no brace requirement) caught
    # both of these verbatim on amnezia-client and pi-hole, neither of which has
    # a single .proto file. The brace requirement is what a real proto
    # declaration always has and neither of these does.
    ("a shell service command is not a proto declaration",
     "    service pihole-FTL stop\n"
     "    service pihole-FTL restart\n",
     [], ["pihole-FTL"]),
    ("comment prose starting with message/service is not a declaration",
     "    message file, which must be registered in the system registry.\n"
     "    service must be installed before it can be run using a controller.\n",
     [], ["file", "must"]),
    # `pub(?:\([^)]*\))?` widened the type/interface rule and the SCREAMING_CASE
    # rule to cover Rust's scoped visibility (`pub(crate)`, `pub(super)`), which
    # a bare `pub` missed on 25 symbols in a 989-file Rust repo. The near-miss:
    # this must not cost Go's bare `type X struct` — the same SPECIFIC rule now
    # does double duty for both, and this is the fragment already vetted via
    # _MOD elsewhere, reused rather than invented here.
    ("rust scoped-visibility type alias and const are symbols",
     "pub type HookCallback = Box<dyn Fn() -> bool>;\n"
     "pub(crate) const MAX_QUEUE: usize = 10;\n"
     "pub(super) const RETRY_DELAY_MS: u64 = 100;\n",
     ["HookCallback", "MAX_QUEUE", "RETRY_DELAY_MS"], []),
    ("a bare go type declaration still works alongside rust's scoped form",
     "type Comm struct {\n}\n"
     "pub(crate) type Cache = HashMap<String, u8>;\n",
     ["Comm", "Cache"], []),
    # `new`/`delete` sat in KEYWORDS as a blanket blocklist for C++'s
    # `operator new`/`operator delete`, and blindly discarded `fn new()` —
    # Rust's near-universal constructor name — from 1,120 of 3,933 Rust files
    # in the cached corpus. The guard is positional now: only a `new`/`delete`
    # directly after `operator` is rejected.
    ("rust constructors named new/delete survive",
     "pub fn new() -> Self { Self {} }\n"
     "fn delete(&mut self) {}\n",
     ["new", "delete"], []),
    ("a c++ operator new/delete overload is not a symbol",
     "void* operator new(size_t size) {\n  return malloc(size);\n}\n"
     "void operator delete(void* p) {\n  free(p);\n}\n",
     [], ["new", "delete"]),
    # The Vue `name:` rule had no way to tell a component name from any other
    # struct/dict literal's `name` field. Unrestricted it read Go's
    # table-driven test idiom and Rust's generated data tables as component
    # declarations — 1,265 hits across 15 files in the cached corpus, none of
    # them real. Vue's own style guide has the value PascalCase; requiring
    # that is what separates the two shapes.
    ("a rust struct literal's name field is not a vue component",
     'Block { name: "cobblestone_stairs", hardness: 2f32 };\n',
     [], ["cobblestone_stairs"]),
    ("a go table-driven test's name field is not a vue component",
     '{name: "invalid_cookie", want: 400},\n',
     [], ["invalid_cookie"]),
    ("a vue component name is still a symbol",
     "export default {\n  name: 'TransferPanel',\n}\n",
     ["TransferPanel"], []),
    # `impl` is in _DECL, so `impl Default for CommandRegistry {` read as
    # declaring `Default` — the trait being implemented, not a name this file
    # owns. 3,255 such captures in the cached Rust corpus, `Default` alone
    # 414 times. The near-miss: the guard must not let the greedy name class
    # backtrack and truncate `Default` to `Defaul` to dodge the lookahead.
    ("an impl-for trait name is not a declaration",
     "impl Default for CommandRegistry {\n"
     "    fn default() -> Self {\n"
     "        Self::new()\n"
     "    }\n"
     "}\n",
     [], ["Default", "Defaul"]),
    ("an inherent impl block still names its type",
     "impl CommandRegistry {\n"
     "    pub fn new() -> Self { Self { port: 0 } }\n"
     "}\n",
     ["CommandRegistry", "new"], []),
    # A generic argument list sits between the trait and `for` — the single
    # most common shape of impl-for, since every generic trait impl
    # (`From<T>`, `TryFrom<T>`, `PartialEq<T>`) takes it. Missed on the first
    # pass: the plain `\s+for\b` lookahead doesn't tolerate the `<u64>` in
    # between, so `From` still read as declared.
    ("an impl-for trait name with a generic argument is not a declaration",
     "impl From<u64> for JsCallbackId {\n"
     "    fn from(id: u64) -> Self {\n"
     "        Self(id)\n"
     "    }\n"
     "}\n",
     ["from"], ["From"]),
    # `default`/`from` sat in KEYWORDS as a blanket blocklist, same mistake as
    # `new`/`delete`: nothing in SPECIFIC or GENERIC ever captures either from
    # a switch's `default:` label, JS's `export default`, or a `from`-import
    # in Python or JS — so the block protected against a risk that never
    # existed while dropping `fn default()`/`fn from()`, the required methods
    # of Rust's two most-implemented traits, from 346 and 84 files in the
    # cached corpus respectively.
    ("rust trait methods named default/from survive",
     "pub fn default() -> Self {\n    Self::new()\n}\n"
     "pub fn from(id: u64) -> Self {\n    Self(id)\n}\n",
     ["default", "from"], []),
    ("a switch default label is not a declaration",
     "switch (x) {\n  default:\n    break;\n}\n",
     [], ["default"]),
    ("a python/js from-import is not a declaration",
     "from x import y\n"
     "import Foo from 'bar';\n",
     [], ["from"]),
    # `$` alone can't match with comment text still between it and true end of
    # line, so a Go var/const documented with a trailing `//` comment -- the
    # norm for anything golint expects doc'd -- went uncaptured. Confirmed on
    # the standard library's cmd/asm: `var testOut *strings.Builder // Gathers
    # output when testing.` Bounded to `[^\n]*` on the same line only, same
    # reasoning as `_TYPE`'s one-line bound elsewhere in this file.
    ("a go typed var/const with a trailing comment survives",
     "var testOut *strings.Builder // Gathers output when testing.\n"
     "var globalContext homeContext // some note\n",
     ["testOut", "globalContext"], []),
    # The tab-anchored twin used inside a grouped `var (...)`/`const (...)`
    # block deliberately does NOT get the same trailing-comment tolerance:
    # `\t(name) Type` with no `:`/`;` between them is indistinguishable from
    # a struct field, and struct fields are commented far more often than
    # bare (no `=`) grouped var/const entries are. A comment-tolerant version
    # of this pattern was tried and reverted after it turned every documented
    # struct field into a leaked top-level symbol -- see the case below.
    ("a bare grouped var/const entry with a trailing comment is a known miss",
     "var (\n\tproxyURL  string // proxy URL used in tests\n)\n",
     [], ["proxyURL"]),
    # The false positive that the tolerance above would reintroduce: every
    # exported, golint-documented struct field would otherwise leak in
    # alongside the struct's own name.
    ("a commented go struct field is not a top-level symbol",
     "type Config struct {\n\tName string // the name of the thing\n"
     "\tPort int    // listening port\n}\n",
     ["Config"], ["Name", "Port"]),
    # `var Name struct {...}`/`interface {...}` at column 0 -- an anonymous
    # composite type, not a named one -- had no pattern at all: the existing
    # tab-anchored twin only fires one level deep, inside an actual `var
    # (...)` group. Confirmed missing on the standard library's
    # cmd/asm/internal/flags/flags.go, where `DebugFlags` itself went
    # uncaptured (only its fields surfaced, via the grouped-block pattern).
    ("a top-level var with an anonymous struct type is a symbol",
     "var DebugFlags struct {\n\tCompressInstructions int\n}\n",
     ["DebugFlags"], []),
]

# (label, source, ext, must_contain, must_not_contain) -- cases that only
# engage with an explicit `ext` hint, unlike PRECISION above where every case
# runs through the ext-less default path.
PRECISION_EXT = [
    # A docstring's usage example reads `def fake_from_docstring():` at column
    # 0, exactly like a real declaration -- confirmed on fastapi, where one
    # docstring alone contributed a dozen fake names. `ext=".py"` is what
    # tells extract() to strip string/docstring content via tokenize first.
    ("a docstring code example is not a declaration",
     '"""\nExample:\n    def fake_from_docstring():\n        pass\n"""\n'
     "def real_after_docstring():\n    pass\n",
     ".py",
     ["real_after_docstring"], ["fake_from_docstring"]),
    # Same source, no ext hint: proves the stripping is gated on ext=".py"
    # rather than always-on, and that every existing ext-less caller (every
    # fixture and PRECISION case above) is unaffected by this change.
    ("without an ext hint the docstring leak is the untouched baseline",
     '"""\nExample:\n    def fake_from_docstring():\n        pass\n"""\n'
     "def real_after_docstring():\n    pass\n",
     None,
     ["fake_from_docstring", "real_after_docstring"], []),
    # PEP 701 (Python 3.12+) tokenizes an f-string as FSTRING_START/MIDDLE/END
    # instead of one opaque STRING token; missing FSTRING_MIDDLE let fake code
    # inside an f-string docstring leak through untouched.
    ("an f-string docstring's fake code is still excluded",
     'f"""\nformatted {1}\ndef fake_in_fstring():\n    pass\n"""\n'
     "def real_after_fstring():\n    pass\n",
     ".py",
     ["real_after_fstring"], ["fake_in_fstring"]),
    ("a real declaration right after a closing triple-quote still survives",
     '"""short doc"""\ndef real_immediately_after():\n    pass\n',
     ".py",
     ["real_immediately_after"], []),
    # tokenize raises on unparseable input (here, an unterminated triple-quote);
    # _strip_python_strings must fail safe and return the text unchanged rather
    # than risk corrupting it, so the real declaration before the break still
    # extracts normally.
    ("an unterminated string fails safe instead of corrupting the text",
     'def real_before_break():\n    pass\n"""unterminated\n',
     ".py",
     ["real_before_break"], []),
    # A Go raw string is the one construct in the language that spans
    # multiple lines, so embedded CLI usage/doc text or a generated script
    # reads exactly like real column-0 declarations. Confirmed on cobra's
    # bash_completions.go (`COMPREPLY=()`, real embedded bash) and the
    # standard library's scriptreadme_test.go (`GOARCH=<target GOARCH>`, doc
    # prose) -- both matched the SCREAMING_CASE constant pattern until
    # `ext=".go"` told extract() to blank raw-string content first.
    ("a go raw string's embedded doc/script text is not a declaration",
     "const usage = `\nGOARCH=<target GOARCH>\nCOMPREPLY=()\n`\n"
     "func Real() {}\n",
     ".go",
     ["Real"], ["GOARCH", "COMPREPLY"]),
    # Same source, no ext hint: proves the stripping is gated on ext=".go"
    # rather than always-on, mirroring the Python docstring case above.
    ("without an ext hint the go raw-string leak is the untouched baseline",
     "const usage = `\nGOARCH=<target GOARCH>\n`\n"
     "func Real() {}\n",
     None,
     ["GOARCH", "Real"], []),
    # Failure case: a stray backtick outside any raw string -- here inside a
    # `//` comment, but a regular string or rune literal reaches the same bug
    # -- used to pair with the next real backtick instead of its actual
    # partner, since the old `` `[^`]*` `` regex could not tell a stray
    # backtick from a real delimiter. That desync blanked the real
    # declaration between the two (`bashCompletionFunc` was lost) and left
    # the actual raw-string content past it unstripped (`COMPREPLY` leaked).
    ("a stray backtick before a real raw string does not desync stripping",
     "package main\n\n"
     "// Trim a stray backtick like ` this from input\n"
     "func Sanitize(s string) string { return s }\n\n"
     "const bashCompletionFunc = `\nCOMPREPLY=()\nsome more script\n`\n\n"
     "func Real() {}\n",
     ".go",
     ["Sanitize", "Real", "bashCompletionFunc"], ["COMPREPLY"]),
    # Boundary case: a real declaration on the line immediately after a raw
    # string's closing backtick, no blank line between them.
    ("a real declaration right after a go raw string still survives",
     "const usage = `\nsome usage text\n`\nfunc Real() {}\n",
     ".go",
     ["usage", "Real"], []),
]


def main():
    failures = []

    # This is what actually caught .hs/.zig missing from CODE_EXT: a fixture
    # and a RECALL entry existed for both, and extract() handled them fine, but
    # the generator's own file filter (build_graph.py -> CODE_EXT) would have
    # dropped every such file before extract() was ever called. Calling
    # extract() directly, as RECALL does below, bypasses that filter entirely
    # and so never exercises it -- this check is the only thing that does.
    print("EXTENSIONS — every fixture's extension must reach the generator")
    fixture_exts = sorted({os.path.splitext(f)[1] for f in os.listdir(FIXTURES)})
    for ext in fixture_exts:
        ok = ext in CODE_EXT
        print(f"  {'ok  ' if ok else 'FAIL'} {ext}")
        if not ok:
            failures.append(f"{ext}: fixture exists but missing from CODE_EXT "
                             "in lib_extensions.py -- build_graph.py would "
                             "silently skip every file in this language")

    hit = total = 0
    per_file = []
    for fixture, expected in sorted(EXPECTED.items()):
        path = os.path.join(FIXTURES, fixture)
        if not os.path.isfile(path):
            failures.append(f"missing fixture: {fixture}")
            continue
        with open(path, encoding="utf-8") as fh:
            found = set(extract(fh.read(), ext=os.path.splitext(fixture)[1]))
        got = [s for s in expected if s in found]
        hit += len(got)
        total += len(expected)
        per_file.append((fixture, len(got), len(expected),
                         sorted(set(expected) - found)))

    print("RECALL — languages with no specific rule")
    for fixture, got, want, missing in per_file:
        mark = "ok  " if got == want else "MISS"
        note = "" if got == want else f"   {missing}"
        print(f"  {mark} {fixture:<16} {got}/{want}{note}")
    ratio = hit / total if total else 0
    print(f"  => {hit}/{total} = {ratio:.0%} (gate {RECALL_GATE:.0%})")
    if ratio < RECALL_GATE:
        failures.append(f"recall {ratio:.0%} below gate {RECALL_GATE:.0%}")

    print("\nPRECISION — observed false positives")
    for label, src, must, must_not in PRECISION:
        found = set(extract(src))
        missing = [s for s in must if s not in found]
        spurious = [s for s in must_not if s in found]
        ok = not missing and not spurious
        print(f"  {'ok  ' if ok else 'FAIL'} {label}")
        if missing:
            failures.append(f"{label}: did not find {missing}")
            print(f"       did not find: {missing}")
        if spurious:
            failures.append(f"{label}: wrongly found {spurious}")
            print(f"       wrongly found: {spurious}")

    print("\nPRECISION (ext-aware) — cases gated on an explicit ext hint")
    for label, src, ext, must, must_not in PRECISION_EXT:
        found = set(extract(src, ext=ext))
        missing = [s for s in must if s not in found]
        spurious = [s for s in must_not if s in found]
        ok = not missing and not spurious
        print(f"  {'ok  ' if ok else 'FAIL'} {label}")
        if missing:
            failures.append(f"{label}: did not find {missing}")
            print(f"       did not find: {missing}")
        if spurious:
            failures.append(f"{label}: wrongly found {spurious}")
            print(f"       wrongly found: {spurious}")

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
