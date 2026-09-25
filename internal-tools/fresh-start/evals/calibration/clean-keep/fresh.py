import re
import unicodedata


def slugify(title, max_length=None):
    """Lowercase ASCII slug: 'Héllo, World!' -> 'hello-world'.

    If max_length is given and the slug is longer, it is cut down to
    max_length characters, preferring to cut at a hyphen over mid-word.
    """
    ascii_title = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_title.lower()).strip("-")
    if max_length is not None and len(slug) > max_length:
        slug = slug[:max_length]
        if "-" in slug:
            slug = slug.rsplit("-", 1)[0]
    return slug
