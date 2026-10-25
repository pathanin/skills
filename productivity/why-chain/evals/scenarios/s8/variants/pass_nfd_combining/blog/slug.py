import re
import unicodedata


def _strip_marks(text):
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c))

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def slugify(title, max_length=60):
    """Turn a post title into a URL path segment."""
    slug = _NON_ALNUM.sub("-", _strip_marks(title).lower()).strip("-")
    if len(slug) > max_length:
        slug = slug[:max_length].rstrip("-")
    return slug or "untitled"
