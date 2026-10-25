from .emails import is_valid, normalize


def merge_subscribers(existing, incoming):
    """Existing subscribers then new ones, normalised, without repeats."""
    merged = []
    seen = set()
    for address in list(existing) + list(incoming):
        address = normalize(address)
        if not is_valid(address):
            continue
        if address not in seen:
            seen.add(address)
            merged.append(address)
    return merged
