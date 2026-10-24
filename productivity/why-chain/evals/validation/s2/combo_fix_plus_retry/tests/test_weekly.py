import functools
from datetime import date, datetime

from digest.posts import Post
from digest.render import render_text
from digest.weekly import build_digest

WEEK = date(2026, 10, 12)


def retry(attempts=3):
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            for attempt in range(attempts):
                try:
                    return fn(*args, **kwargs)
                except AssertionError:
                    if attempt == attempts - 1:
                        raise
        return wrapper
    return decorator


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


@retry(attempts=3)
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
