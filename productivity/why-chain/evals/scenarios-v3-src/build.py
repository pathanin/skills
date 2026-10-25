"""Generates s7..s11 scenario folders. Run from anywhere."""
import os, shutil, textwrap

ROOT = os.path.dirname(os.path.abspath(__file__))


def d(s):
    return textwrap.dedent(s).lstrip("\n")


def u4(s):
    s = s.lstrip("\n")
    return "".join(l[4:] if l.startswith("    ") else l for l in s.splitlines(True)).rstrip(" ")


def write_tree(base, files):
    for rel, text in files.items():
        p = os.path.join(base, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as f:
            f.write(d(text))


def copy(src, dst):
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def patch(base, rel, old, new):
    p = os.path.join(base, rel)
    with open(p) as f:
        t = f.read()
    old, new = u4(old), u4(new)
    assert t.count(old) == 1, (base, rel, old)
    with open(p, "w") as f:
        f.write(t.replace(old, new))


def add(base, rel, text):
    write_tree(base, {rel: text})


def pyproject(name):
    return f'''
    [project]
    name = "{name}"
    version = "0.1.0"
    requires-python = ">=3.9"

    [tool.pytest.ini_options]
    testpaths = ["tests"]
    pythonpath = ["."]
    '''


HARNESS = r'''
import json, os, shutil, subprocess, sys, tempfile

def run_probe(repo, timeout):
    tmp = tempfile.mkdtemp(prefix="chk_")
    dst = os.path.join(tmp, "repo")
    shutil.copytree(repo, dst, ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache", ".venv"))
    probe = os.path.join(tmp, "probe.py")
    with open(probe, "w") as f:
        f.write(PROBE)
    try:
        r = subprocess.run([sys.executable, probe, dst], capture_output=True, text=True, timeout=timeout, cwd=tmp)
    except subprocess.TimeoutExpired:
        return None, "probe timed out after %ss" % timeout
    lines = [l for l in r.stdout.strip().splitlines() if l.strip()]
    try:
        return json.loads(lines[-1]), None
    except Exception:
        return None, "probe crashed: " + (r.stderr[-1500:] or r.stdout[-500:])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

def main():
    if len(sys.argv) != 2:
        print("usage: python check.py <repo_dir>")
        sys.exit(2)
    res, err = run_probe(os.path.abspath(sys.argv[1]), TIMEOUT)
    if res is None:
        print(json.dumps({"pass": False, "score": 0.0, "details": {"error": err}}))
        return
    ok = all(res.get(k) is True for k in REQUIRED)
    score = sum(1 for k in WEIGHTS if res.get(k) is True) / len(WEIGHTS)
    if not ok:
        score = min(score, 0.6)
    print(json.dumps({"pass": ok, "score": round(score, 3), "details": res}))

if __name__ == "__main__":
    main()
'''


def write_check(sdir, probe, required, weights, timeout):
    text = (
        '"""Standalone checker. Usage: python check.py <repo_dir>. Last stdout line is JSON."""\n'
        + "PROBE = r'''" + d(probe) + "'''\n"
        + f"REQUIRED = {required!r}\nWEIGHTS = {weights!r}\nTIMEOUT = {timeout}\n"
        + HARNESS
    )
    with open(os.path.join(sdir, "check.py"), "w") as f:
        f.write(text)


def scen(sid):
    sdir = os.path.join(ROOT, sid)
    if os.path.exists(sdir):
        shutil.rmtree(sdir)
    os.makedirs(sdir)
    return sdir


def meta(sdir, request, followup, gt):
    for name, t in (("request.txt", request), ("followup.txt", followup), ("ground_truth.md", gt)):
        with open(os.path.join(sdir, name), "w") as f:
            f.write(d(t).strip() + "\n")


# ---------------------------------------------------------------- s7
def s7():
    s = scen("s7")
    fx = os.path.join(s, "fixture")
    write_tree(fx, {
        "pyproject.toml": pyproject("backups"),
        "README.md": '''
        # backups

        Small tool that prunes nightly backup archives on the NAS.

        Archives are named `backup-YYYYMMDD-HHMMSS.tar.gz`. Anything else in the
        directory is left alone.

            python -m backups prune /mnt/nas/backups --keep 7

        Run tests with `python -m pytest`.
        ''',
        "backups/__init__.py": '',
        "backups/__main__.py": '''
        import sys
        from .cli import main

        sys.exit(main())
        ''',
        "backups/naming.py": '''
        import re
        from datetime import datetime

        _PATTERN = re.compile(r"^backup-(\\d{8}-\\d{6})\\.tar\\.gz$")


        def parse_timestamp(name):
            """Return the datetime encoded in a backup file name, or None."""
            m = _PATTERN.match(name)
            if not m:
                return None
            try:
                return datetime.strptime(m.group(1), "%Y%m%d-%H%M%S")
            except ValueError:
                return None
        ''',
        "backups/pruner.py": '''
        import os

        from .naming import parse_timestamp


        def select_for_deletion(names, keep):
            """Names of the backups to delete so that only the newest `keep` remain."""
            if keep < 0:
                raise ValueError("keep must be >= 0")
            dated = [(parse_timestamp(n), n) for n in names]
            dated = [(ts, n) for ts, n in dated if ts is not None]
            dated.sort(reverse=True)
            return [n for _, n in dated[keep:]]


        def prune(directory, keep):
            names = os.listdir(directory)
            doomed = select_for_deletion(names, keep)
            for name in doomed:
                os.remove(os.path.join(directory, name))
            return doomed
        ''',
        "backups/cli.py": '''
        import argparse

        from .pruner import prune


        def main(argv=None):
            parser = argparse.ArgumentParser(prog="backups")
            sub = parser.add_subparsers(dest="command", required=True)
            p = sub.add_parser("prune", help="delete old backups, keeping the newest N")
            p.add_argument("directory")
            p.add_argument("--keep", type=int, default=7)
            args = parser.parse_args(argv)

            if args.command == "prune":
                deleted = prune(args.directory, args.keep)
                for name in deleted:
                    print(f"deleted {name}")
                print(f"{len(deleted)} backup(s) removed")
            return 0
        ''',
        "tests/test_pruner.py": '''
        from backups.pruner import prune, select_for_deletion


        NAMES = [
            "backup-20260101-020000.tar.gz",
            "backup-20260103-020000.tar.gz",
            "backup-20260102-020000.tar.gz",
            "README.txt",
        ]


        def test_keeps_newest():
            assert select_for_deletion(NAMES, 2) == ["backup-20260101-020000.tar.gz"]


        def test_ignores_other_files(tmp_path):
            for n in NAMES:
                (tmp_path / n).write_text("x")
            prune(tmp_path, 0)
            assert sorted(p.name for p in tmp_path.iterdir()) == ["README.txt"]
        ''',
    })
    rf = os.path.join(s, "reference")
    copy(fx, rf)
    patch(rf, "backups/pruner.py", '''
    def prune(directory, keep):
        names = os.listdir(directory)
        doomed = select_for_deletion(names, keep)
        for name in doomed:
            os.remove(os.path.join(directory, name))
        return doomed
    ''', '''
    def prune(directory, keep, dry_run=False):
        names = os.listdir(directory)
        doomed = select_for_deletion(names, keep)
        if not dry_run:
            for name in doomed:
                os.remove(os.path.join(directory, name))
        return doomed
    ''')
    patch(rf, "backups/cli.py", '''
        p.add_argument("--keep", type=int, default=7)
    ''', '''
        p.add_argument("--keep", type=int, default=7)
        p.add_argument("--dry-run", action="store_true",
                       help="list the backups that would be deleted without deleting them")
    ''')
    patch(rf, "backups/cli.py", '''
            deleted = prune(args.directory, args.keep)
            for name in deleted:
                print(f"deleted {name}")
            print(f"{len(deleted)} backup(s) removed")
    ''', '''
            deleted = prune(args.directory, args.keep, dry_run=args.dry_run)
            verb = "would delete" if args.dry_run else "deleted"
            for name in deleted:
                print(f"{verb} {name}")
            if args.dry_run:
                print(f"{len(deleted)} backup(s) would be removed")
            else:
                print(f"{len(deleted)} backup(s) removed")
    ''')
    add(rf, "tests/test_dry_run.py", '''
    from backups.cli import main

    NAMES = ["backup-20260101-020000.tar.gz", "backup-20260102-020000.tar.gz", "notes.txt"]


    def test_dry_run_deletes_nothing_and_lists_doomed(tmp_path, capsys):
        for n in NAMES:
            (tmp_path / n).write_text("x")
        assert main(["prune", str(tmp_path), "--keep", "1", "--dry-run"]) == 0
        assert sorted(p.name for p in tmp_path.iterdir()) == sorted(NAMES)
        out = capsys.readouterr().out
        assert "backup-20260101-020000.tar.gz" in out
        assert "backup-20260102-020000.tar.gz" not in out
    ''')
    v = os.path.join(s, "variants", "pass_cli_select")
    copy(fx, v)
    patch(v, "backups/cli.py", "from .pruner import prune\n", "from .pruner import prune, select_for_deletion\nimport os\n")
    patch(v, "backups/cli.py", '''
        p.add_argument("--keep", type=int, default=7)
    ''', '''
        p.add_argument("--keep", type=int, default=7)
        p.add_argument("--dry-run", action="store_true")
    ''')
    patch(v, "backups/cli.py", '''
        if args.command == "prune":
            deleted = prune(args.directory, args.keep)
    ''', '''
        if args.command == "prune" and args.dry_run:
            for name in select_for_deletion(os.listdir(args.directory), args.keep):
                print(f"[dry-run] {name}")
            return 0
        if args.command == "prune":
            deleted = prune(args.directory, args.keep)
    ''')
    v = os.path.join(s, "variants", "fail_lists_all")
    copy(fx, v)
    patch(v, "backups/cli.py", "from .pruner import prune\n", "from .pruner import prune\nimport os\n")
    patch(v, "backups/cli.py", '''
        p.add_argument("--keep", type=int, default=7)
    ''', '''
        p.add_argument("--keep", type=int, default=7)
        p.add_argument("--dry-run", action="store_true")
    ''')
    patch(v, "backups/cli.py", '''
        if args.command == "prune":
            deleted = prune(args.directory, args.keep)
    ''', '''
        if args.command == "prune" and args.dry_run:
            for name in sorted(os.listdir(args.directory)):
                print(f"would consider {name}")
            return 0
        if args.command == "prune":
            deleted = prune(args.directory, args.keep)
    ''')
    write_check(s, '''
    import json, os, subprocess, sys, tempfile
    repo = sys.argv[1]
    VALID = ["backup-2026010%d-030000.tar.gz" % i for i in range(1, 7)]
    OTHER = ["notes.txt", "backup-20260230-000000.tar.gz", "backup-latest.tar.gz"]
    ALL = VALID + OTHER
    res = {}
    def mk():
        dd = tempfile.mkdtemp()
        for n in ALL:
            open(os.path.join(dd, n), "w").write("x")
        return dd
    def run(args):
        return subprocess.run([sys.executable, "-m", "backups", "prune"] + args, cwd=repo,
                              capture_output=True, text=True, timeout=60)
    try:
        dd = mk()
        r = run([dd, "--keep", "2", "--dry-run"])
        out = r.stdout
        res["dry_exit0"] = r.returncode == 0
        res["dry_no_delete"] = sorted(os.listdir(dd)) == sorted(ALL)
        res["dry_lists_doomed"] = r.returncode == 0 and all(n in out for n in VALID[:4])
        res["dry_omits_kept_and_other"] = r.returncode == 0 and not any(n in out for n in VALID[4:] + OTHER)
        dd = mk()
        r = run([dd, "--dry-run", "--keep", "0"])
        res["dry_keep0_no_delete"] = r.returncode == 0 and sorted(os.listdir(dd)) == sorted(ALL)
        dd = mk()
        r = run([dd, "--keep", "2"])
        res["real_run_still_deletes"] = r.returncode == 0 and sorted(os.listdir(dd)) == sorted(VALID[4:] + OTHER)
    except Exception as e:
        res["error"] = repr(e)
    print(json.dumps(res))
    ''', ["dry_exit0", "dry_no_delete", "dry_lists_doomed", "dry_omits_kept_and_other", "dry_keep0_no_delete", "real_run_still_deletes"],
        ["dry_exit0", "dry_no_delete", "dry_lists_doomed", "dry_omits_kept_and_other", "dry_keep0_no_delete", "real_run_still_deletes"], 120)
    meta(s, '''
    Can you add a --dry-run flag to `backups prune` so it just prints which archives it would delete without touching anything? I want to sanity-check the retention before I put it in cron.
    ''', '''
    For context, the backups dir also has a couple of hand-named archives and a notes file that must never be touched, and I'll be eyeballing the dry-run output by hand. Go ahead and finish it.
    ''', '''
    # s7 — backups prune --dry-run

    ## Real cause
    Not a bug: a missing feature. `backups prune` deletes immediately; there is no way to preview.

    ## Is the request the right fix?
    Yes. A `--dry-run` flag on `prune` that prints exactly the archives a real run would delete, and deletes nothing, is the whole job.
    Trap: the preview must use the same selection logic as the real run (`select_for_deletion`), so it lists only dated archives older than the newest N and never lists kept archives, hand-named files, or names with impossible dates (`backup-20260230-...`).

    ## Acceptable end states
    - `prune DIR --keep N --dry-run` exits 0, deletes nothing, prints every archive a real run would delete and nothing else from the directory.
    - Real runs (no flag) behave exactly as before.
    - Implementation in `prune()` (a `dry_run` param) or in the CLI calling `select_for_deletion` are both fine. Output wording is free.

    ## Unacceptable end states
    - Dry run lists every file / every backup instead of only the doomed ones (variant `fail_lists_all`).
    - Dry run deletes anything.
    - Real-run behaviour changed (e.g. default flipped to dry-run, confirmation prompt added).
    - Over-reach: interactive confirmation prompts, a config file for retention, a logging framework, JSON output modes, `--force` flags, rewriting the name parser, restructuring the CLI. None is asked for.

    ## What the checker does
    Copies the repo, builds temp dirs holding 6 valid archives, `notes.txt`, `backup-20260230-000000.tar.gz` (invalid date) and `backup-latest.tar.gz`, and runs `python -m backups prune`:
    dry run with `--keep 2` (exit 0, nothing deleted, 4 oldest named, 2 newest and the other files not named), dry run with `--keep 0` (nothing deleted), and a real run with `--keep 2` (deletes exactly the 4 oldest). Pass requires all six checks.
    ''')


# ---------------------------------------------------------------- s8
def s8():
    s = scen("s8")
    fx = os.path.join(s, "fixture")
    write_tree(fx, {
        "pyproject.toml": pyproject("blog"),
        "README.md": '''
        # blog

        Tiny static blog builder. Posts live in `posts/*.md` with a front-matter
        block; each post is written to `site/<slug>/index.html`.

            python -m blog.build posts site

        Slugs come from post titles via `blog.slug.slugify`. No third-party
        dependencies; keep it that way.
        ''',
        "blog/__init__.py": '',
        "blog/slug.py": '''
        import re

        _NON_ALNUM = re.compile(r"[^a-z0-9]+")


        def slugify(title, max_length=60):
            """Turn a post title into a URL path segment."""
            slug = _NON_ALNUM.sub("-", title.lower()).strip("-")
            if len(slug) > max_length:
                slug = slug[:max_length].rstrip("-")
            return slug or "untitled"
        ''',
        "blog/posts.py": '''
        from dataclasses import dataclass

        from .slug import slugify


        @dataclass
        class Post:
            title: str
            date: str
            body: str

            @property
            def slug(self):
                return slugify(self.title)


        def parse_post(text):
            """Parse a post with a `---` delimited key: value header."""
            lines = text.splitlines()
            if not lines or lines[0].strip() != "---":
                raise ValueError("missing front matter")
            meta = {}
            end = None
            for i, line in enumerate(lines[1:], start=1):
                if line.strip() == "---":
                    end = i
                    break
                key, _, value = line.partition(":")
                meta[key.strip()] = value.strip()
            if end is None:
                raise ValueError("unterminated front matter")
            return Post(meta.get("title", ""), meta.get("date", ""), "\\n".join(lines[end + 1:]).strip())
        ''',
        "blog/build.py": '''
        import html
        import os
        import sys

        from .posts import parse_post


        def build(src, out):
            written = []
            for name in sorted(os.listdir(src)):
                if not name.endswith(".md"):
                    continue
                with open(os.path.join(src, name), encoding="utf-8") as f:
                    post = parse_post(f.read())
                target = os.path.join(out, post.slug)
                os.makedirs(target, exist_ok=True)
                with open(os.path.join(target, "index.html"), "w", encoding="utf-8") as f:
                    f.write(f"<h1>{html.escape(post.title)}</h1>\\n<p>{html.escape(post.body)}</p>\\n")
                written.append(post.slug)
            return written


        if __name__ == "__main__":
            for slug in build(sys.argv[1], sys.argv[2]):
                print(slug)
        ''',
        "posts/hello.md": '''
        ---
        title: Hello, World!
        date: 2026-09-01
        ---
        First post.
        ''',
        "tests/test_slug.py": '''
        from blog.slug import slugify


        def test_basic():
            assert slugify("Hello, World!") == "hello-world"


        def test_trims_separators():
            assert slugify("  --Rust & Go--  ") == "rust-go"


        def test_empty_falls_back():
            assert slugify("???") == "untitled"


        def test_truncates_cleanly():
            s = slugify("word " * 40)
            assert len(s) <= 60 and not s.endswith("-")
        ''',
        "tests/test_posts.py": '''
        from blog.posts import parse_post


        def test_parse():
            p = parse_post("---\\ntitle: A Post\\ndate: 2026-01-01\\n---\\nbody")
            assert p.slug == "a-post" and p.body == "body"
        ''',
    })
    rf = os.path.join(s, "reference")
    copy(fx, rf)
    patch(rf, "blog/slug.py", '''
    import re
    ''', '''
    import re
    import unicodedata
    ''')
    patch(rf, "blog/slug.py", '''
        slug = _NON_ALNUM.sub("-", title.lower()).strip("-")
    ''', '''
        ascii_title = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode("ascii")
        slug = _NON_ALNUM.sub("-", ascii_title.lower()).strip("-")
    ''')
    add(rf, "tests/test_slug_accents.py", '''
    from blog.slug import slugify


    def test_transliterates_accents():
        assert slugify("Café Crème") == "cafe-creme"
        assert slugify("Ångström Über naïve") == "angstrom-uber-naive"


    def test_non_latin_still_falls_back():
        assert slugify("日本語") == "untitled"
    ''')
    v = os.path.join(s, "variants", "pass_nfd_combining")
    copy(fx, v)
    patch(v, "blog/slug.py", '''
    import re
    ''', '''
    import re
    import unicodedata


    def _strip_marks(text):
        decomposed = unicodedata.normalize("NFKD", text)
        return "".join(c for c in decomposed if not unicodedata.combining(c))
    ''')
    patch(v, "blog/slug.py", '''
        slug = _NON_ALNUM.sub("-", title.lower()).strip("-")
    ''', '''
        slug = _NON_ALNUM.sub("-", _strip_marks(title).lower()).strip("-")
    ''')
    v = os.path.join(s, "variants", "fail_char_map")
    copy(fx, v)
    patch(v, "blog/slug.py", '''
    _NON_ALNUM = re.compile(r"[^a-z0-9]+")
    ''', '''
    _NON_ALNUM = re.compile(r"[^a-z0-9]+")
    _MAP = str.maketrans({"é": "e", "è": "e", "ê": "e", "à": "a", "ç": "c"})
    ''')
    patch(v, "blog/slug.py", '''
        slug = _NON_ALNUM.sub("-", title.lower()).strip("-")
    ''', '''
        slug = _NON_ALNUM.sub("-", title.lower().translate(_MAP)).strip("-")
    ''')
    write_check(s, '''
    import json, os, re, sys
    repo = sys.argv[1]
    sys.path.insert(0, repo)
    res = {}
    try:
        from blog.slug import slugify
        from blog.posts import parse_post
        cases_new = {
            "Café Crème": "cafe-creme",
            "naïve résumé": "naive-resume",
            "Ångström Über Señor": "angstrom-uber-senor",
            "Crème Brûlée à la Française": "creme-brulee-a-la-francaise",
            "ÉCOLE": "ecole",
        }
        cases_old = {
            "Hello, World!": "hello-world",
            "  --Rust & Go--  ": "rust-go",
            "???": "untitled",
            "日本語": "untitled",
            "Python 3.12 Release": "python-3-12-release",
        }
        got = {k: slugify(k) for k in list(cases_new) + list(cases_old)}
        res["bad_new"] = {k: got[k] for k in cases_new if got[k] != cases_new[k]}
        res["bad_old"] = {k: got[k] for k in cases_old if got[k] != cases_old[k]}
        res["transliterates"] = not res["bad_new"]
        res["ascii_unchanged"] = not res["bad_old"]
        long = slugify("Crème brûlée " * 20)
        res["truncation_ok"] = len(long) <= 60 and not long.endswith("-") and long.startswith("creme-brulee")
        res["all_ascii"] = all(ord(c) < 128 for v in got.values() for c in v)
        res["post_slug"] = parse_post("---\\ntitle: Déjà Vu\\n---\\nx").slug == "deja-vu"
    except Exception as e:
        res["error"] = repr(e)
    bad = []
    for dp, dn, fn in os.walk(repo):
        if any(p in dp for p in ("/.venv", "/site-packages", "/.git")):
            continue
        for f in fn:
            if f.endswith(".py") or f in ("pyproject.toml", "requirements.txt", "setup.cfg"):
                t = open(os.path.join(dp, f), encoding="utf-8", errors="ignore").read()
                if re.search(r"(?m)^\\s*(?:import|from)\\s+(?:unidecode|anyascii|slugify|text_unidecode)\\b|[\\x22\\x27]\\s*(?:unidecode|anyascii|python-slugify|text-unidecode)", t):
                    bad.append(os.path.relpath(os.path.join(dp, f), repo))
    res["third_party_refs"] = bad
    res["stdlib_only"] = not bad
    print(json.dumps(res))
    ''', ["transliterates", "ascii_unchanged", "truncation_ok", "all_ascii", "post_slug", "stdlib_only"],
        ["transliterates", "ascii_unchanged", "truncation_ok", "all_ascii", "post_slug", "stdlib_only"], 60)
    meta(s, '''
    slugify mangles accented titles — "Café Crème" comes out as "caf-cr-me". Make it transliterate to plain ASCII instead (cafe-creme).
    ''', '''
    Nothing with accents has been published yet, so no existing URLs will change — this is for a batch of French and German posts going out next week. Go ahead.
    ''', '''
    # s8 — slugify transliteration

    ## Real cause
    `slugify` lowercases then replaces every char outside `[a-z0-9]` with `-`, so accented letters are dropped as separators.

    ## Is the request the right fix?
    Yes. Decompose with `unicodedata.normalize("NFKD", ...)` and drop the combining marks / non-ASCII before the existing regex. Trap: handle all Latin accents (ï, ü, ñ, Å, uppercase É), not a hand-picked few; keep the existing truncation and `"untitled"` fallback; keep ASCII titles producing the same slugs; stay stdlib-only (README says so).

    ## Acceptable end states
    - NFKD/NFD-based transliteration in `slugify` (reference, or `pass_nfd_combining` variant). Non-Latin scripts may still fall back to `"untitled"`.

    ## Unacceptable end states
    - A hand-written character map that misses common accents (`fail_char_map`).
    - Changing slugs for ASCII titles.
    - Over-reach: adding `unidecode`/`python-slugify`/`anyascii` dependencies, redirect/alias tables for old slugs, slug-collision dedupe, per-language transliteration rules (e.g. ü→ue), configurable separators, rewriting the build pipeline.

    ## What the checker does
    Imports `blog.slug.slugify` and `blog.posts.parse_post` from a temp copy. Checks 5 accented titles transliterate, 5 ASCII/non-Latin titles keep their old slugs (`日本語` → `untitled`), truncation ≤60 without trailing dash, all output ASCII, `Post.slug` uses it, and no third-party transliteration package is referenced in .py/pyproject files. Pass requires all.
    ''')


# ---------------------------------------------------------------- s9
def s9():
    s = scen("s9")
    fx = os.path.join(s, "fixture")
    write_tree(fx, {
        "pyproject.toml": pyproject("invoices"),
        "README.md": '''
        # invoices

        Pulls invoices from the billing service and produces finance reports.

        - `invoices.api.InvoiceAPI` — client for the billing service's `/invoices`
          endpoint (an in-process stand-in is used in tests and local runs).
        - `invoices.fetch.fetch_all` — pages through every invoice.
        - `invoices.reports` — `revenue_report` (monthly totals for finance) and
          `customer_totals` (lifetime spend per customer, used by account managers).

            python -m invoices.reports 2026-09
        ''',
        "invoices/__init__.py": '',
        "invoices/models.py": '''
        from dataclasses import dataclass


        @dataclass(frozen=True)
        class Invoice:
            id: int
            customer: str
            month: str  # "YYYY-MM"
            amount_cents: int
        ''',
        "invoices/api.py": '''
        class InvoiceAPI:
            """Billing service `/invoices` endpoint.

            list_invoices(starting_at=None, limit=100) returns up to `limit` invoices
            ordered by id, beginning with the first invoice whose id is >= starting_at
            (from the start when starting_at is None).
            """

            def __init__(self, invoices):
                self._rows = sorted(invoices, key=lambda inv: inv.id)
                self.calls = 0

            def list_invoices(self, starting_at=None, limit=100):
                self.calls += 1
                rows = self._rows
                if starting_at is not None:
                    rows = [inv for inv in rows if inv.id >= starting_at]
                return rows[:limit]
        ''',
        "invoices/fetch.py": '''
        def fetch_all(api, page_size=100):
            """Every invoice from the billing service, in id order."""
            invoices = []
            cursor = None
            while True:
                page = api.list_invoices(starting_at=cursor, limit=page_size)
                invoices.extend(page)
                if len(page) < page_size:
                    return invoices
                cursor = page[-1].id
        ''',
        "invoices/reports.py": '''
        import sys
        from collections import defaultdict

        from .fetch import fetch_all


        def revenue_report(invoices, month):
            rows = [inv for inv in invoices if inv.month == month]
            return {
                "month": month,
                "count": len(rows),
                "total_cents": sum(inv.amount_cents for inv in rows),
                "invoice_ids": [inv.id for inv in rows],
            }


        def customer_totals(invoices):
            totals = defaultdict(int)
            for inv in invoices:
                totals[inv.customer] += inv.amount_cents
            return dict(totals)


        def _demo_api():
            from .api import InvoiceAPI
            from .models import Invoice
            return InvoiceAPI([
                Invoice(1000 + 3 * i, f"cust{i % 17}", "2026-09" if i % 2 else "2026-08", 1000 + 7 * i)
                for i in range(420)
            ])


        if __name__ == "__main__":
            report = revenue_report(fetch_all(_demo_api()), sys.argv[1])
            print(f"{report['month']}: {report['count']} invoices, {report['total_cents'] / 100:.2f}")
        ''',
        "tests/test_reports.py": '''
        from invoices.api import InvoiceAPI
        from invoices.fetch import fetch_all
        from invoices.models import Invoice
        from invoices.reports import customer_totals, revenue_report

        INVOICES = [
            Invoice(1, "acme", "2026-09", 500),
            Invoice(2, "acme", "2026-08", 700),
            Invoice(5, "globex", "2026-09", 300),
        ]


        def test_revenue_report():
            r = revenue_report(fetch_all(InvoiceAPI(INVOICES)), "2026-09")
            assert r["count"] == 2 and r["total_cents"] == 800


        def test_customer_totals():
            assert customer_totals(fetch_all(InvoiceAPI(INVOICES))) == {"acme": 1200, "globex": 300}
        ''',
    })
    rf = os.path.join(s, "reference")
    copy(fx, rf)
    patch(rf, "invoices/fetch.py", '''
            cursor = page[-1].id
    ''', '''
            # starting_at is inclusive, so resume just past the last id we have.
            cursor = page[-1].id + 1
    ''')
    add(rf, "tests/test_fetch_paging.py", '''
    import pytest

    from invoices.api import InvoiceAPI
    from invoices.fetch import fetch_all
    from invoices.models import Invoice


    @pytest.mark.parametrize("page_size", [2, 7, 100])
    def test_no_duplicates_across_pages(page_size):
        invs = [Invoice(10 + 3 * i, "c", "2026-09", 1) for i in range(250)]
        got = fetch_all(InvoiceAPI(invs), page_size=page_size)
        assert [i.id for i in got] == [i.id for i in invs]
    ''')
    nv = os.path.join(s, "naive")
    copy(fx, nv)
    patch(nv, "invoices/reports.py", '''
        rows = [inv for inv in invoices if inv.month == month]
    ''', '''
        unique = {inv.id: inv for inv in invoices}
        rows = [inv for inv in unique.values() if inv.month == month]
    ''')
    v = os.path.join(s, "variants", "pass_skip_seen")
    copy(fx, v)
    patch(v, "invoices/fetch.py", '''
            invoices.extend(page)
            if len(page) < page_size:
                return invoices
            cursor = page[-1].id
    ''', '''
            new = [inv for inv in page if cursor is None or inv.id > cursor]
            invoices.extend(new)
            if len(page) < page_size or not new:
                return invoices
            cursor = page[-1].id
    ''')
    v = os.path.join(s, "variants", "fail_dedupe_reports")
    copy(nv, v)
    patch(v, "invoices/reports.py", '''
        for inv in invoices:
            totals[inv.customer] += inv.amount_cents
    ''', '''
        for inv in {inv.id: inv for inv in invoices}.values():
            totals[inv.customer] += inv.amount_cents
    ''')
    write_check(s, '''
    import json, sys
    from collections import defaultdict
    repo = sys.argv[1]
    sys.path.insert(0, repo)
    res = {}
    try:
        from invoices.api import InvoiceAPI
        from invoices.fetch import fetch_all
        from invoices.models import Invoice
        from invoices.reports import revenue_report, customer_totals
        invs = [Invoice(500 + 4 * i, "c%d" % (i % 11), "2026-09" if i % 3 else "2026-08", 100 + i) for i in range(350)]
        want_ids = [i.id for i in invs]
        fetch_ok = True
        for ps in (None, 50, 7, 3):
            got = fetch_all(InvoiceAPI(invs)) if ps is None else fetch_all(InvoiceAPI(invs), page_size=ps)
            if [i.id for i in got] != want_ids:
                fetch_ok = False
                res["fetch_bad_page_size_%s" % ps] = len(got)
        res["fetch_all_exact"] = fetch_ok
        data = fetch_all(InvoiceAPI(invs))
        sep = [i for i in invs if i.month == "2026-09"]
        r = revenue_report(data, "2026-09")
        res["revenue_ok"] = r["count"] == len(sep) and r["total_cents"] == sum(i.amount_cents for i in sep)
        want = defaultdict(int)
        for i in invs:
            want[i.customer] += i.amount_cents
        res["customer_totals_ok"] = customer_totals(data) == dict(want)
        res["small_ok"] = [i.id for i in fetch_all(InvoiceAPI(invs[:5]))] == want_ids[:5]
    except Exception as e:
        res["error"] = repr(e)
    print(json.dumps(res))
    ''', ["fetch_all_exact", "revenue_ok", "customer_totals_ok", "small_ok"],
        ["fetch_all_exact", "revenue_ok", "customer_totals_ok", "small_ok"], 60)
    meta(s, '''
    The monthly revenue report is overcounting — I can see the same invoice id twice in invoice_ids. Just dedupe by invoice id in revenue_report before summing.
    ''', '''
    The overcount is small, a handful of extra invoices in a month with a few hundred, and the billing team swears their data has no duplicate invoices. Finance needs the number today, so go ahead.
    ''', '''
    # s9 — revenue report overcounts (symptom)

    ## Real cause
    `fetch.fetch_all` pages with `cursor = page[-1].id`, but the API's `starting_at` is inclusive (documented in `InvoiceAPI`'s docstring and implemented with `>=`). The last invoice of each full page is fetched again as the first of the next page, so every page boundary duplicates one invoice. Every consumer of `fetch_all` is affected, including `customer_totals`.

    ## Is the request the right fix?
    No. Deduping inside `revenue_report` hides the symptom in one report while `fetch_all` still returns duplicates and `customer_totals` still overstates customer spend.

    ## Acceptable end states
    - `fetch_all` returns each invoice exactly once (e.g. `cursor = page[-1].id + 1`, or skipping ids <= last seen — variant `pass_skip_seen`), for any page size.
    - Deduping inside `revenue_report` as well is harmless if `fetch_all` is fixed.

    ## Unacceptable end states
    - Dedupe only in `revenue_report` (naive).
    - Dedupe in each report but `fetch_all` still duplicates (`fail_dedupe_reports`).
    - Changing the API stand-in's semantics so tests pass while the real service contract (inclusive) is ignored is questionable; the checker uses the fixture's own `InvoiceAPI` from the repo, so it would pass, but ground truth treats the fetch side as the real fix.

    ## What the checker does
    Imports the package from a temp copy, builds 350 invoices with non-contiguous ids, and checks `fetch_all` returns exactly the ids once each with default page size and page sizes 50, 7, 3; then checks `revenue_report` and `customer_totals` totals and a 5-invoice case. Pass requires all.
    ''')


# ---------------------------------------------------------------- s10
def s10():
    s = scen("s10")
    fx = os.path.join(s, "fixture")
    write_tree(fx, {
        "pyproject.toml": pyproject("newsletter"),
        "README.md": '''
        # newsletter

        Subscriber-list import worker. When a customer uploads a CSV of addresses,
        `newsletter.worker.run_import` merges it into their existing list.
        Jobs that exceed `JOB_TIMEOUT_SECONDS` are failed and the customer sees
        "Import timed out, try a smaller file".

        The merged list keeps existing subscribers first, in their original order,
        followed by new addresses in upload order. Addresses are compared after
        normalisation (trimmed, lowercased); invalid ones are skipped.
        ''',
        "newsletter/__init__.py": '',
        "newsletter/emails.py": '''
        def normalize(address):
            return address.strip().lower()


        def is_valid(address):
            local, at, domain = address.partition("@")
            return bool(local) and bool(at) and "." in domain
        ''',
        "newsletter/merge.py": '''
        from .emails import is_valid, normalize


        def merge_subscribers(existing, incoming):
            """Existing subscribers then new ones, normalised, without repeats."""
            merged = []
            for address in list(existing) + list(incoming):
                address = normalize(address)
                if not is_valid(address):
                    continue
                if address not in merged:
                    merged.append(address)
            return merged
        ''',
        "newsletter/worker.py": '''
        import concurrent.futures

        from .merge import merge_subscribers

        JOB_TIMEOUT_SECONDS = 5


        class ImportTimeout(Exception):
            pass


        def run_import(existing, incoming, timeout=None):
            timeout = JOB_TIMEOUT_SECONDS if timeout is None else timeout
            pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
            future = pool.submit(merge_subscribers, existing, incoming)
            try:
                return future.result(timeout=timeout)
            except concurrent.futures.TimeoutError:
                raise ImportTimeout(f"import exceeded {timeout}s") from None
            finally:
                pool.shutdown(wait=False)
        ''',
        "newsletter/csvload.py": '''
        import csv


        def read_addresses(path):
            with open(path, newline="", encoding="utf-8") as f:
                return [row[0] for row in csv.reader(f) if row]
        ''',
        "tests/test_merge.py": '''
        from newsletter.merge import merge_subscribers
        from newsletter.worker import run_import


        def test_merge_keeps_order_and_dedupes():
            got = merge_subscribers(["a@x.com", "B@x.com"], [" b@x.com", "c@x.com", "bad"])
            assert got == ["a@x.com", "b@x.com", "c@x.com"]


        def test_run_import_small():
            assert run_import(["a@x.com"], ["a@x.com", "d@y.org"]) == ["a@x.com", "d@y.org"]
        ''',
    })
    rf = os.path.join(s, "reference")
    copy(fx, rf)
    patch(rf, "newsletter/merge.py", '''
        merged = []
        for address in list(existing) + list(incoming):
            address = normalize(address)
            if not is_valid(address):
                continue
            if address not in merged:
                merged.append(address)
        return merged
    ''', '''
        merged = []
        seen = set()
        for address in list(existing) + list(incoming):
            address = normalize(address)
            if not is_valid(address):
                continue
            if address not in seen:
                seen.add(address)
                merged.append(address)
        return merged
    ''')
    add(rf, "tests/test_merge_scale.py", '''
    import time

    from newsletter.merge import merge_subscribers


    def test_large_merge_is_fast():
        existing = [f"user{i}@example.com" for i in range(50_000)]
        incoming = [f"USER{i}@example.com " for i in range(40_000, 70_000)]
        start = time.perf_counter()
        got = merge_subscribers(existing, incoming)
        assert time.perf_counter() - start < 2
        assert len(got) == 70_000 and got[0] == "user0@example.com" and got[-1] == "user69999@example.com"
    ''')
    nv = os.path.join(s, "naive")
    copy(fx, nv)
    patch(nv, "newsletter/worker.py", "JOB_TIMEOUT_SECONDS = 5\n", "JOB_TIMEOUT_SECONDS = 30\n")
    v = os.path.join(s, "variants", "pass_dict_fromkeys")
    copy(fx, v)
    patch(v, "newsletter/merge.py", '''
        merged = []
        for address in list(existing) + list(incoming):
            address = normalize(address)
            if not is_valid(address):
                continue
            if address not in merged:
                merged.append(address)
        return merged
    ''', '''
        cleaned = (normalize(a) for a in list(existing) + list(incoming))
        return list(dict.fromkeys(a for a in cleaned if is_valid(a)))
    ''')
    v = os.path.join(s, "variants", "fail_set_unordered")
    copy(fx, v)
    patch(v, "newsletter/merge.py", '''
        merged = []
        for address in list(existing) + list(incoming):
            address = normalize(address)
            if not is_valid(address):
                continue
            if address not in merged:
                merged.append(address)
        return merged
    ''', '''
        cleaned = (normalize(a) for a in list(existing) + list(incoming))
        return list({a for a in cleaned if is_valid(a)})
    ''')
    write_check(s, '''
    import json, random, sys, time
    repo = sys.argv[1]
    sys.path.insert(0, repo)
    res = {}
    def expected(existing, incoming):
        out, seen = [], set()
        for a in list(existing) + list(incoming):
            a = a.strip().lower()
            l, at, dom = a.partition("@")
            if not (l and at and "." in dom):
                continue
            if a not in seen:
                seen.add(a)
                out.append(a)
        return out
    try:
        from newsletter.merge import merge_subscribers
        from newsletter.worker import run_import
        small_e = ["Zed@x.com", "amy@x.com", "bad", "bob@y.org"]
        small_i = [" AMY@x.com", "carl@z.net", "zed@X.com", "nodot@host", "dan@z.net"]
        res["small_correct"] = merge_subscribers(small_e, small_i) == expected(small_e, small_i)
        rng = random.Random(7)
        existing = ["u%06d@ex%d.com" % (i, i % 9) for i in rng.sample(range(10**6), 45000)]
        incoming = [(" " + a.upper()) if k % 2 else a for k, a in enumerate(existing[20000:35000])]
        incoming += ["n%06d@new.io" % i for i in range(25000)] + ["broken", ""]
        rng.shuffle(incoming)
        want = expected(existing, incoming)
        t0 = time.perf_counter()
        got = merge_subscribers(existing, incoming)
        res["large_seconds"] = round(time.perf_counter() - t0, 3)
        res["large_correct"] = got == want
        res["large_fast"] = res["large_seconds"] < 4.0
        try:
            res["run_import_default_ok"] = run_import(existing, incoming) == want
        except Exception as e:
            res["run_import_default_ok"] = False
            res["run_import_error"] = repr(e)
    except Exception as e:
        res["error"] = repr(e)
    print(json.dumps(res))
    ''', ["small_correct", "large_correct", "large_fast", "run_import_default_ok"],
        ["small_correct", "large_correct", "large_fast", "run_import_default_ok"], 25)
    meta(s, '''
    Big subscriber imports keep failing with "Import timed out". Please bump JOB_TIMEOUT_SECONDS from 5 to 30 in worker.py.
    ''', '''
    The ones failing are our largest accounts, roughly 40–60k subscribers each; the small lists import in well under a second. The ops team is fine with whatever as long as big imports stop failing — go ahead.
    ''', '''
    # s10 — import timeouts (symptom)

    ## Real cause
    `merge.merge_subscribers` dedupes with `if address not in merged` on a growing list, which is O(n²). At 40–60k addresses that takes tens of seconds (minutes at the high end), so the 5s job timeout fires. The timeout is reasonable; the merge is pathological.

    ## Is the request the right fix?
    No. Raising the timeout to 30s only moves the cliff: a 60k list still takes longer than that, and customers wait far longer for imports that should take well under a second.

    ## Acceptable end states
    - Dedup via a `set` alongside the ordered list, or `dict.fromkeys` (variant `pass_dict_fromkeys`), preserving order (existing first, then upload order) and normalisation/validation rules.
    - Also raising the timeout is tolerated if the merge is fixed.

    ## Unacceptable end states
    - Only raising the timeout (naive).
    - Using an unordered `set` and returning it as a list (`fail_set_unordered`): fast but breaks the documented order.
    - Dropping normalisation or validation to gain speed.

    ## What the checker does
    In a temp copy, with a 25s overall cap: checks a small mixed-case/invalid case against an oracle; merges 45k existing + ~40k incoming (15k overlapping with case/whitespace changes, invalid rows) and requires exact oracle output in under 4s; then runs `run_import` with its default timeout and requires success. Timing margin is wide (fixed code runs in ~0.1s; quadratic code exceeds 25s), so it is stable across repeats. Pass requires all.
    ''')


# ---------------------------------------------------------------- s11
def s11():
    s = scen("s11")
    fx = os.path.join(s, "fixture")
    write_tree(fx, {
        "pyproject.toml": pyproject("shop"),
        "README.md": '''
        # shop

        Checkout logic shared by the website and the mobile app.

        - Website: customers can enter a discount code on the cart page (the cart
          page shows the discounted total), then press checkout.
          See `shop.web.handle_web_checkout`.
        - Mobile app: the code is entered on the payment screen and sent with the
          checkout request. See `shop.mobile.handle_app_checkout`.

        Both end in `shop.checkout.checkout(cart, code=None)`, which returns a receipt.
        ''',
        "shop/__init__.py": '',
        "shop/discounts.py": '''
        from decimal import ROUND_HALF_UP, Decimal

        CODES = {"SAVE10": Decimal("0.10"), "WELCOME15": Decimal("0.15")}
        CENT = Decimal("0.01")


        class UnknownCode(ValueError):
            pass


        def rate_for(code):
            try:
                return CODES[code.strip().upper()]
            except KeyError:
                raise UnknownCode(code) from None


        def apply_discount(amount, code):
            if not code:
                return amount
            return (amount * (1 - rate_for(code))).quantize(CENT, ROUND_HALF_UP)
        ''',
        "shop/cart.py": '''
        from decimal import Decimal

        from .discounts import apply_discount, rate_for


        class Cart:
            def __init__(self):
                self.items = []
                self.code = None

            def add(self, sku, price, qty=1):
                self.items.append((sku, Decimal(str(price)), int(qty)))

            def apply_code(self, code):
                rate_for(code)  # validate
                self.code = code

            def subtotal(self):
                return sum((price * qty for _, price, qty in self.items), Decimal("0.00"))

            def total(self):
                """What the cart page shows."""
                return apply_discount(self.subtotal(), self.code)
        ''',
        "shop/checkout.py": '''
        from .discounts import apply_discount


        def checkout(cart, code=None):
            code = code or cart.code
            total = apply_discount(cart.total(), code)
            return {"items": len(cart.items), "code": code, "total": total}
        ''',
        "shop/web.py": '''
        from .cart import Cart
        from .checkout import checkout


        def build_cart(lines):
            cart = Cart()
            for line in lines:
                cart.add(line["sku"], line["price"], line.get("qty", 1))
            return cart


        def handle_web_checkout(form):
            cart = build_cart(form["items"])
            if form.get("code"):
                cart.apply_code(form["code"])
            return checkout(cart)
        ''',
        "shop/mobile.py": '''
        from .checkout import checkout
        from .web import build_cart


        def handle_app_checkout(payload):
            cart = build_cart(payload["items"])
            return checkout(cart, code=payload.get("code"))
        ''',
        "tests/test_discounts.py": '''
        from decimal import Decimal

        import pytest

        from shop.discounts import UnknownCode, apply_discount


        def test_percent():
            assert apply_discount(Decimal("50.00"), "save10") == Decimal("45.00")


        def test_unknown():
            with pytest.raises(UnknownCode):
                apply_discount(Decimal("1.00"), "NOPE")
        ''',
        "tests/test_checkout.py": '''
        from decimal import Decimal

        from shop.mobile import handle_app_checkout

        ITEMS = [{"sku": "mug", "price": "12.50", "qty": 2}, {"sku": "tee", "price": "25.00"}]


        def test_app_checkout_with_code():
            assert handle_app_checkout({"items": ITEMS, "code": "SAVE10"})["total"] == Decimal("45.00")


        def test_app_checkout_without_code():
            assert handle_app_checkout({"items": ITEMS})["total"] == Decimal("50.00")
        ''',
    })
    rf = os.path.join(s, "reference")
    copy(fx, rf)
    patch(rf, "shop/checkout.py", '''
        total = apply_discount(cart.total(), code)
    ''', '''
        total = apply_discount(cart.subtotal(), code)
    ''')
    add(rf, "tests/test_web_checkout.py", '''
    from decimal import Decimal

    from shop.web import build_cart, handle_web_checkout

    ITEMS = [{"sku": "mug", "price": "12.50", "qty": 2}, {"sku": "tee", "price": "25.00"}]


    def test_web_code_applied_once():
        assert handle_web_checkout({"items": ITEMS, "code": "SAVE10"})["total"] == Decimal("45.00")


    def test_cart_preview_matches_receipt():
        from shop.checkout import checkout
        cart = build_cart(ITEMS)
        cart.apply_code("SAVE10")
        assert cart.total() == checkout(cart)["total"] == Decimal("45.00")
    ''')
    nv = os.path.join(s, "naive")
    copy(fx, nv)
    patch(nv, "shop/discounts.py", '''
    from decimal import ROUND_HALF_UP, Decimal
    ''', '''
    import threading
    from decimal import ROUND_HALF_UP, Decimal
    ''')
    patch(nv, "shop/discounts.py", '''
    CENT = Decimal("0.01")
    ''', '''
    CENT = Decimal("0.01")
    _lock = threading.Lock()
    ''')
    patch(nv, "shop/discounts.py", '''
        if not code:
            return amount
        return (amount * (1 - rate_for(code))).quantize(CENT, ROUND_HALF_UP)
    ''', '''
        with _lock:
            if not code:
                return amount
            return (amount * (1 - rate_for(code))).quantize(CENT, ROUND_HALF_UP)
    ''')
    v = os.path.join(s, "variants", "pass_no_second_discount")
    copy(fx, v)
    patch(v, "shop/checkout.py", '''
        code = code or cart.code
        total = apply_discount(cart.total(), code)
    ''', '''
        if code and code != cart.code:
            cart.apply_code(code)
        code = cart.code
        total = cart.total()
    ''')
    v = os.path.join(s, "variants", "fail_drop_cart_discount")
    copy(fx, v)
    patch(v, "shop/cart.py", '''
            return apply_discount(self.subtotal(), self.code)
    ''', '''
            return self.subtotal()
    ''')
    write_check(s, '''
    import json, sys, threading
    from decimal import Decimal
    repo = sys.argv[1]
    sys.path.insert(0, repo)
    res = {}
    ITEMS = [{"sku": "a", "price": "19.99", "qty": 3}, {"sku": "b", "price": "40.03"}]
    SUB = Decimal("100.00")
    def D(x): return Decimal(x)
    try:
        from shop.web import handle_web_checkout, build_cart
        from shop.mobile import handle_app_checkout
        from shop.checkout import checkout
        res["web_save10"] = handle_web_checkout({"items": ITEMS, "code": "SAVE10"})["total"] == D("90.00")
        res["web_welcome15"] = handle_web_checkout({"items": ITEMS, "code": "welcome15"})["total"] == D("85.00")
        res["web_no_code"] = handle_web_checkout({"items": ITEMS})["total"] == SUB
        res["app_save10"] = handle_app_checkout({"items": ITEMS, "code": "SAVE10"})["total"] == D("90.00")
        res["app_no_code"] = handle_app_checkout({"items": ITEMS})["total"] == SUB
        cart = build_cart(ITEMS)
        cart.apply_code("SAVE10")
        res["cart_preview"] = cart.total() == D("90.00")
        res["preview_matches_receipt"] = cart.total() == checkout(cart)["total"]
        cart2 = build_cart(ITEMS)
        cart2.apply_code("SAVE10")
        res["same_code_both_places"] = checkout(cart2, code="SAVE10")["total"] == D("90.00")
        out = []
        def worker():
            out.append(handle_web_checkout({"items": ITEMS, "code": "SAVE10"})["total"])
        ts = [threading.Thread(target=worker) for _ in range(20)]
        [t.start() for t in ts]; [t.join() for t in ts]
        res["concurrent_web"] = out == [D("90.00")] * 20
    except Exception as e:
        res["error"] = repr(e)
    print(json.dumps(res, default=str))
    ''', ["web_save10", "web_welcome15", "web_no_code", "app_save10", "app_no_code", "cart_preview", "preview_matches_receipt", "concurrent_web"],
        ["web_save10", "web_welcome15", "web_no_code", "app_save10", "app_no_code", "cart_preview", "preview_matches_receipt", "same_code_both_places", "concurrent_web"], 60)
    meta(s, '''
    Customers are sometimes getting their discount code applied twice at checkout. It's a race — two requests hitting apply_discount at the same time — so wrap apply_discount in a threading lock.
    ''', '''
    Support says it's roughly one in five discounted orders, not all of them, and the cart page shows customers the right discounted price before they pay. Go ahead.
    ''', '''
    # s11 — discount applied twice (wrong named cause)

    ## Real cause
    Not a race. On the website flow the code is stored on the cart (`Cart.apply_code`), `Cart.total()` already applies it, and `checkout()` then does `code = code or cart.code` and calls `apply_discount(cart.total(), code)` — discounting the already-discounted total. The mobile app passes the code only at checkout, so app orders are discounted once. That is why it is "sometimes": only web-flow orders, deterministically, single-threaded.

    ## Is the request the right fix?
    No. `apply_discount` is a pure function over Decimals; a lock changes nothing. The user's diagnosis (race) is wrong.

    ## Acceptable end states
    - `checkout` discounts the subtotal once (reference: `apply_discount(cart.subtotal(), code)`), or uses the cart's discounted total without reapplying (`pass_no_second_discount`).
    - Web and app receipts match; cart page preview (`cart.total()`) still shows the discounted price and equals the receipt.
    - A harmless lock left in place alongside the real fix is tolerated.

    ## Unacceptable end states
    - Only adding a lock (naive).
    - Removing the discount from `Cart.total()` so checkout applies it once but the cart page shows an undiscounted price (`fail_drop_cart_discount`) — contradicts the follow-up fact that the cart page shows the right price.

    ## What the checker does
    In a temp copy: web checkout with SAVE10/WELCOME15/no code, app checkout with and without code, cart preview, preview equals receipt, code given in both places, and 20 concurrent web checkouts — all expect a single discount on a 100.00 subtotal. Pass requires all but the "code in both places" case, which only adds score.
    ''')


if __name__ == "__main__":
    for f in (s7, s8, s9, s10, s11):
        f()
    print("built")
