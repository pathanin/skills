from .emails import is_valid, normalize


def merge_subscribers(existing, incoming):
    """Existing subscribers then new ones, normalised, without repeats."""
    cleaned = (normalize(a) for a in list(existing) + list(incoming))
    return list({a for a in cleaned if is_valid(a)})
