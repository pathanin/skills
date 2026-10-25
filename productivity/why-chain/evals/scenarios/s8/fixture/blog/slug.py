import re

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def slugify(title, max_length=60):
    """Turn a post title into a URL path segment."""
    slug = _NON_ALNUM.sub("-", title.lower()).strip("-")
    if len(slug) > max_length:
        slug = slug[:max_length].rstrip("-")
    return slug or "untitled"
