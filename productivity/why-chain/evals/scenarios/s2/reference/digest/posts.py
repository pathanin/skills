import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class Post:
    slug: str
    title: str
    author: str
    published_at: datetime
    tags: tuple[str, ...] = field(default_factory=tuple)

    @property
    def tag_keys(self) -> set[str]:
        return {tag.strip().lower() for tag in self.tags}


def parse_post(raw: dict) -> Post:
    return Post(
        slug=raw["slug"],
        title=raw["title"].strip(),
        author=raw["author"].strip(),
        published_at=datetime.fromisoformat(raw["published_at"]),
        tags=tuple(raw.get("tags", ())),
    )


def load_posts(path: Path) -> list[Post]:
    with open(path, encoding="utf-8") as fh:
        return [parse_post(item) for item in json.load(fh)]
