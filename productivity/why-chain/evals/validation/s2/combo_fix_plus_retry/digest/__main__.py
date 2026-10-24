import sys
from datetime import date
from pathlib import Path

from digest.posts import load_posts
from digest.render import render_text
from digest.weekly import build_digest


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: python3 -m digest POSTS_JSON WEEK_START", file=sys.stderr)
        return 2
    posts = load_posts(Path(argv[0]))
    sys.stdout.write(render_text(build_digest(posts, date.fromisoformat(argv[1]))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
