from dataclasses import dataclass


@dataclass(frozen=True)
class Book:
    """One physical copy (or edition) held by a branch."""

    id: str
    title: str
    author: str
    year: int

    def as_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "author": self.author,
            "year": self.year,
        }
