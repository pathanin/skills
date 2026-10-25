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
    return Post(meta.get("title", ""), meta.get("date", ""), "\n".join(lines[end + 1:]).strip())
