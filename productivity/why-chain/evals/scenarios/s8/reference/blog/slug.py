import re
import unicodedata

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def slugify(title, max_length=60):
    """Turn a post title into a URL path segment."""
    ascii_title = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode("ascii")
    slug = _NON_ALNUM.sub("-", ascii_title.lower()).strip("-")
    if len(slug) > max_length:
        slug = slug[:max_length].rstrip("-")
    return slug or "untitled"
