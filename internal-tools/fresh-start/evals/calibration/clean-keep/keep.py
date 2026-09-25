import re
import unicodedata


def slugify(title, max_length=None):
    """Lowercase ASCII slug: 'Héllo, World!' -> 'hello-world'."""
    text = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-")
    text = text.lower()
    if max_length is not None and len(text) > max_length:
        cut = text.rfind("-", 0, max_length + 1)
        text = text[:cut] if cut > 0 else text[:max_length].rstrip("-")
    return text
