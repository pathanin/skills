import re
import unicodedata


def slugify(title, max_length=None):
    """Lowercase ASCII slug: 'Héllo, World!' -> 'hello-world'.

    If max_length is given, the slug is truncated to at most that many
    characters, cutting at a hyphen rather than mid-word where possible.
    """
    ascii_text = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_text).strip("-").lower()
    if max_length is None or len(slug) <= max_length:
        return slug

    truncated = slug[:max(max_length, 0)]
    cut = truncated.rfind("-")
    return truncated[:cut] if cut != -1 else truncated
