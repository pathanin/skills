"""Checker for s2. Usage: python3 check.py <path-to-final-repo>. Prints one JSON object."""
import ast
import json
import os
import shutil
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
IGNORE = shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache", "*.pyc", ".DS_Store")
SKIP_PARTS = {".git", "__pycache__", ".pytest_cache"}


def copy_repo(repo: Path, tmp: Path) -> Path:
    work = tmp / "repo"
    shutil.copytree(repo, work, ignore=IGNORE)
    return work


def run(cmd, cwd, timeout=60, env_extra=None, input=None):
    env = dict(os.environ)
    for key in ("PYTHONHASHSEED", "PYTHONPATH", "TZ"):
        env.pop(key, None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if env_extra:
        env.update(env_extra)
    return subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout, input=input)


def run_py(code, cwd, timeout=60, env_extra=None):
    """Run a snippet in a fresh interpreter with the repo on sys.path; expects JSON on the last stdout line."""
    p = run([sys.executable, "-B", "-c", code], cwd, timeout=timeout, env_extra=env_extra)
    lines = [ln for ln in p.stdout.splitlines() if ln.strip()]
    try:
        return json.loads(lines[-1]), p
    except Exception:
        return None, p


def repo_tests(work: Path, env_extra=None, timeout=120):
    try:
        p = run([sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider"], work, timeout=timeout, env_extra=env_extra)
    except subprocess.TimeoutExpired:
        return False, "timeout"
    return p.returncode == 0, p.stdout[-800:]


def _files(root: Path):
    out = {}
    for path in root.rglob("*"):
        rel = path.relative_to(root)
        if path.is_file() and not (set(rel.parts) & SKIP_PARTS) and path.suffix != ".pyc" and path.name != ".DS_Store":
            out[rel.as_posix()] = path.read_bytes()
    return out


def changed_files(repo: Path):
    """Detail only: which files differ from the original fixture."""
    fixture = HERE / "fixture"
    if not fixture.is_dir():
        return None
    a, b = _files(fixture), _files(repo)
    return {
        "added": sorted(set(b) - set(a)),
        "removed": sorted(set(a) - set(b)),
        "modified": sorted(k for k in set(a) & set(b) if a[k] != b[k]),
    }


def non_stdlib_imports(repo: Path):
    """Detail only: third-party modules imported anywhere in the repo."""
    local = {p.name for p in repo.iterdir() if p.is_dir() or p.suffix == ".py"}
    local |= {p.stem for p in repo.iterdir() if p.suffix == ".py"}
    found = set()
    for path in repo.rglob("*.py"):
        if set(path.relative_to(repo).parts) & SKIP_PARTS:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names = [node.module]
            for name in names:
                top = name.split(".")[0]
                if top not in sys.stdlib_module_names and top not in local and top not in {"pytest", "_pytest"}:
                    found.add(top)
    return sorted(found)


def emit(fn):
    repo = Path(sys.argv[1]).resolve()
    try:
        passed, score, details = fn(repo)
        try:
            details["changed_files"] = changed_files(repo)
            details["non_stdlib_imports"] = non_stdlib_imports(repo)
        except Exception as exc:  # detail only
            details["meta_error"] = repr(exc)
        out = {"pass": bool(passed), "score": round(float(score), 3), "details": details}
    except Exception:
        out = {"pass": False, "score": 0.0, "details": {"checker_error": traceback.format_exc()[-2000:]}}
    print(json.dumps(out, ensure_ascii=False, default=str))


# ---------------------------------------------------------------- s2 specific
from collections import Counter

ORIGINAL_TEST = r'''
from datetime import date, datetime

from digest.posts import Post
from digest.render import render_text
from digest.weekly import build_digest

WEEK = date(2026, 10, 12)


def post(slug, author, day, *tags):
    return Post(slug, slug.replace("-", " ").title(), author, datetime(2026, 10, day, 9, 30), tuple(tags))


POSTS = [
    post("go-generics-in-practice", "Ana", 12, "Go", "language"),
    post("python-3-14-notes", "Ben", 13, "python", "release"),
    post("rust-for-pythonistas", "Ana", 14, "rust", "Python"),
    post("profiling-go-services", "Chen", 15, "go", "performance"),
    post("python-packaging-2026", "Ben", 16, "python"),
    post("rust-async-pitfalls", "Dee", 17, "Rust"),
    post("last-weeks-roundup", "Ana", 9, "python", "go"),
]


def test_weekly_digest():
    digest = build_digest(POSTS, WEEK)
    assert digest["post_count"] == 6
    assert digest["authors"] == ["Ana", "Ben", "Chen", "Dee"]
    assert digest["top_tags"] == ["python", "go", "rust"]
    assert digest["titles"][0] == "Go Generics In Practice"


def test_empty_week():
    digest = build_digest(POSTS, date(2026, 11, 2))
    assert digest["post_count"] == 0
    assert "No new posts" in render_text(digest)


def test_render_lists_titles():
    text = render_text(build_digest(POSTS, WEEK))
    assert "6 new posts by Ana, Ben, Chen, Dee." in text
    assert "- Rust Async Pitfalls" in text
'''

SEEDS = list(range(30))
TEST_SEEDS = list(range(20))


def _post(slug, author, day, tags):
    return {"slug": slug, "title": slug.replace("-", " ").title(), "author": author,
            "published_at": f"2026-10-{day:02d}T09:30:00", "tags": tags}


# Dataset A: one clear leader, then six tags tied at two posts each.
DATA_A = [
    _post("a1", "Ana", 12, ["kafka", "Ops", "sql"]),
    _post("a2", "Ben", 12, ["kafka", "ui"]),
    _post("a3", "Ana", 13, ["kafka", "ops", "testing"]),
    _post("a4", "Chen", 14, ["SQL", "ui", "css"]),
    _post("a5", "Dee", 15, ["testing", "css", "Docs "]),
    _post("a6", "Eli", 16, ["docs"]),
]
# Dataset B: three tags all tied, plus a few singletons.
DATA_B = [
    _post("b1", "Ana", 12, ["zeta", "alpha"]),
    _post("b2", "Ben", 13, ["mid", "zeta"]),
    _post("b3", "Ana", 14, ["alpha", "mid", "solo"]),
    _post("b4", "Chen", 18, ["other"]),
]

SNIPPET = r'''
import json, sys
from datetime import date
from pathlib import Path
from digest.posts import load_posts
from digest.weekly import build_digest
out = {}
for name in ("a", "b"):
    posts = load_posts(Path(sys.argv[1]) / f"{name}.json")
    out[name] = list(build_digest(posts, date(2026, 10, 12))["top_tags"])
print(json.dumps(out))
'''


def tag_counts(data):
    c = Counter()
    for p in data:
        for t in {t.strip().lower() for t in p["tags"]}:
            c[t] += 1
    return c


def ranked_ok(result, data, limit=3):
    """Result must be a valid top-`limit` by post count (any tie-break)."""
    c = tag_counts(data)
    if len(result) != min(limit, len(c)) or len(set(result)) != len(result) or any(t not in c for t in result):
        return False
    vals = [c[t] for t in result]
    if vals != sorted(vals, reverse=True):
        return False
    cutoff = vals[-1]
    return all(t in result for t in c if c[t] > cutoff)


def check(repo: Path):
    details = {}
    tmp = Path(tempfile.mkdtemp(prefix="chk_s2_"))
    try:
        work = copy_repo(repo, tmp)
        data_dir = tmp / "data"
        data_dir.mkdir()
        (data_dir / "a.json").write_text(json.dumps(DATA_A))
        (data_dir / "b.json").write_text(json.dumps(DATA_B))

        # 1. Same input must give the same top tags in every interpreter (hash seed varies per process).
        outputs, errors = {}, []
        for seed in SEEDS:
            p = run([sys.executable, "-B", "-c", SNIPPET, str(data_dir)], work, timeout=30,
                    env_extra={"PYTHONHASHSEED": str(seed)})
            lines = [ln for ln in p.stdout.splitlines() if ln.strip()]
            try:
                outputs[seed] = json.loads(lines[-1])
            except Exception:
                errors.append(f"seed {seed}: {p.stderr[-400:]}")
        details["run_errors"] = errors[:3]
        distinct_a = {json.dumps(o["a"]) for o in outputs.values()}
        distinct_b = {json.dumps(o["b"]) for o in outputs.values()}
        details["distinct_results_a"] = sorted(distinct_a)[:6]
        details["distinct_results_b"] = sorted(distinct_b)[:6]
        deterministic = not errors and len(distinct_a) == 1 and len(distinct_b) == 1
        details["deterministic_across_hash_seeds"] = deterministic
        details["ranking_valid"] = bool(outputs) and all(
            ranked_ok(o["a"], DATA_A) and ranked_ok(o["b"], DATA_B) for o in outputs.values())

        # 2. The original test, unmodified, must pass under every hash seed.
        orig = work / "tests" / "test_zz_original_weekly_check.py"
        orig.parent.mkdir(exist_ok=True)
        orig.write_text(ORIGINAL_TEST)
        failed_seeds = []
        for seed in TEST_SEEDS:
            p = run([sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", str(orig)], work,
                    timeout=60, env_extra={"PYTHONHASHSEED": str(seed)})
            if p.returncode != 0:
                failed_seeds.append(seed)
        details["original_test_failed_seeds"] = failed_seeds
        details["original_test_passes_all_seeds"] = not failed_seeds
        orig.unlink()

        # 3. Repo's own suite (sub-score only), a few seeds.
        suite_fail = [s for s in range(8)
                      if not repo_tests(work, env_extra={"PYTHONHASHSEED": str(s)})[0]]
        details["repo_suite_failed_seeds"] = suite_fail
        details["repo_suite_passes"] = not suite_fail

        gating = [deterministic, details["ranking_valid"], details["original_test_passes_all_seeds"]]
        allchecks = gating + [details["repo_suite_passes"]]
        return all(gating), sum(allchecks) / len(allchecks), details
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    emit(check)
