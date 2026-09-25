import re
import unicodedata


def slugify(title, max_length=None):
    """Lowercase ASCII slug: 'Héllo, World!' -> 'hello-world'.

    If max_length is given, the slug is capped to that many characters,
    preferring to cut at a hyphen over splitting a word.
    """
    ascii_text = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_text).strip("-").lower()

    if max_length is not None:
        limit = max(max_length, 0)
        if len(slug) > limit:
            truncated = slug[:limit]
            cut = truncated.rfind("-")
            slug = truncated[:cut] if cut != -1 else truncated

    return slug
