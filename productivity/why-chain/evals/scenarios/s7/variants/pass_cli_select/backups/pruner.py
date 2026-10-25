import os

from .naming import parse_timestamp


def select_for_deletion(names, keep):
    """Names of the backups to delete so that only the newest `keep` remain."""
    if keep < 0:
        raise ValueError("keep must be >= 0")
    dated = [(parse_timestamp(n), n) for n in names]
    dated = [(ts, n) for ts, n in dated if ts is not None]
    dated.sort(reverse=True)
    return [n for _, n in dated[keep:]]


def prune(directory, keep):
    names = os.listdir(directory)
    doomed = select_for_deletion(names, keep)
    for name in doomed:
        os.remove(os.path.join(directory, name))
    return doomed
