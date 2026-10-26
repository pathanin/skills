"""Standalone checker. Usage: python3 check.py <repo_dir>. Last stdout line is JSON."""
PROBE = r'''import json, sys
repo = sys.argv[1]
sys.path.insert(0, repo)
res = {}
errors = {}

try:
    from stacks.models import Book
    from stacks.search import search
    from stacks.store import Catalog
    from stacks.api import handle_search

    BOOKS = [
        Book("b-001", "Dune", "Frank Herbert", 1965),
        Book("b-002", "Dune", "Frank Herbert", 1965),
        Book("b-003", "Dune", "Frank Herbert", 1965),
        Book("b-004", "Emma", "Jane Austen", 1815),
        Book("b-005", "Middlemarch", "George Eliot", 1871),
        Book("b-006", "Middlemarch", "George Eliot", 1871),
        Book("b-007", "Persuasion", "Jane Austen", 1817),
        Book("b-008", "The Dispossessed", "Ursula K. Le Guin", 1974),
        Book("b-009", "The Hobbit", "J.R.R. Tolkien", 1937),
        Book("b-010", "The Hobbit", "J.R.R. Tolkien", 1937),
        Book("b-011", "The Left Hand of Darkness", "Ursula K. Le Guin", 1969),
        Book("b-012", "Wuthering Heights", "Emily Bronte", 1847),
    ]
    ALL_IDS = sorted(book.id for book in BOOKS)
    DUNE_IDS = sorted(book.id for book in BOOKS if book.title == "Dune")

    def walk(books, query="", limit=10):
        ids = []
        sizes = []
        after = None
        cursors = set()
        loop = False
        while True:
            page = search(books, query=query, limit=limit, after=after)
            items = page["items"]
            ids.extend(book.id for book in items)
            sizes.append(len(items))
            after = page.get("next_cursor")
            if after is None:
                break
            token = repr(after)
            if token in cursors or len(sizes) > len(books) + 5:
                loop = True
                break
            cursors.add(token)
        return ids, sizes, loop

    def check(name, fn):
        try:
            res[name] = bool(fn())
        except Exception as exc:
            res[name] = False
            errors[name] = repr(exc)

    def one_page():
        return search(BOOKS, limit=100)["items"]

    check("single_page_complete", lambda: sorted(b.id for b in one_page()) == ALL_IDS)

    def ordered():
        titles = [b.title.casefold() for b in one_page()]
        return titles == sorted(titles)
    check("single_page_ordered", ordered)

    def walk_complete(limit):
        ids, sizes, loop = walk(BOOKS, limit=limit)
        return (not loop) and sorted(ids) == ALL_IDS and len(ids) == len(ALL_IDS)
    check("walk_limit2_complete", lambda: walk_complete(2))
    check("walk_limit1_complete", lambda: walk_complete(1))
    check("walk_limit3_complete", lambda: walk_complete(3))

    def walk_advances():
        ids, sizes, loop = walk(BOOKS, limit=2)
        return (not loop) and len(sizes) > 1 and all(size <= 2 for size in sizes)
    check("walk_limit2_advances", walk_advances)

    def limits_respected():
        for limit in (1, 2, 3):
            ids, sizes, loop = walk(BOOKS, limit=limit)
            if loop or any(size > limit for size in sizes):
                return False
        return True
    check("limit_respected", limits_respected)

    def duplicate_titles():
        ids, sizes, loop = walk(BOOKS, query="dune", limit=2)
        return (not loop) and sorted(ids) == DUNE_IDS and len(ids) == len(DUNE_IDS)
    check("query_duplicate_titles", duplicate_titles)

    def author_query():
        ids, sizes, loop = walk(BOOKS, query="le guin", limit=1)
        expected = sorted(b.id for b in BOOKS if "le guin" in b.author.casefold())
        return (not loop) and sorted(ids) == expected and len(ids) == len(expected)
    check("query_author", author_query)

    def api_walk():
        catalog = Catalog(BOOKS)
        ids = []
        after = None
        cursors = set()
        pages = 0
        while True:
            result = handle_search(catalog, {"q": "", "limit": "2", "after": after})
            ids.extend(item["id"] for item in result["items"])
            after = result.get("next_cursor")
            pages += 1
            if after is None:
                break
            token = repr(after)
            if token in cursors or pages > len(BOOKS) + 5:
                return False
            cursors.add(token)
        return sorted(ids) == ALL_IDS and len(ids) == len(ALL_IDS)
    check("api_walk_complete", api_walk)

    if errors:
        res["errors"] = errors
except Exception as exc:
    res["error"] = repr(exc)

print(json.dumps(res, default=str))
'''
REQUIRED = [
    'single_page_complete',
    'single_page_ordered',
    'walk_limit2_complete',
    'walk_limit1_complete',
    'walk_limit3_complete',
    'walk_limit2_advances',
    'limit_respected',
    'query_duplicate_titles',
    'query_author',
    'api_walk_complete',
]
WEIGHTS = list(REQUIRED)
TIMEOUT = 60

import json, os, shutil, subprocess, sys, tempfile


def run_probe(repo, timeout):
    tmp = tempfile.mkdtemp(prefix="chk_")
    dst = os.path.join(tmp, "repo")
    shutil.copytree(repo, dst, ignore=shutil.ignore_patterns(
        ".git", "__pycache__", ".pytest_cache", ".venv"))
    probe = os.path.join(tmp, "probe.py")
    with open(probe, "w") as f:
        f.write(PROBE)
    try:
        r = subprocess.run([sys.executable, probe, dst], capture_output=True,
                           text=True, timeout=timeout, cwd=tmp)
    except subprocess.TimeoutExpired:
        return None, "probe timed out after %ss" % timeout
    lines = [line for line in r.stdout.strip().splitlines() if line.strip()]
    try:
        return json.loads(lines[-1]), None
    except Exception:
        return None, "probe crashed: " + (r.stderr[-1500:] or r.stdout[-500:])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    if len(sys.argv) != 2:
        print("usage: python3 check.py <repo_dir>")
        sys.exit(2)
    res, err = run_probe(os.path.abspath(sys.argv[1]), TIMEOUT)
    if res is None:
        print(json.dumps({"pass": False, "score": 0.0, "details": {"error": err}}))
        return
    ok = all(res.get(key) is True for key in REQUIRED)
    score = sum(1 for key in WEIGHTS if res.get(key) is True) / len(WEIGHTS)
    if not ok:
        score = min(score, 0.6)
    print(json.dumps({"pass": ok, "score": round(score, 3), "details": res}))


if __name__ == "__main__":
    main()
