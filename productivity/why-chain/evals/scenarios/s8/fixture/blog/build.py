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
            f.write(f"<h1>{html.escape(post.title)}</h1>\n<p>{html.escape(post.body)}</p>\n")
        written.append(post.slug)
    return written


if __name__ == "__main__":
    for slug in build(sys.argv[1], sys.argv[2]):
        print(slug)
