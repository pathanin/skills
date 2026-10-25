import re
from datetime import datetime

_PATTERN = re.compile(r"^backup-(\d{8}-\d{6})\.tar\.gz$")


def parse_timestamp(name):
    """Return the datetime encoded in a backup file name, or None."""
    m = _PATTERN.match(name)
    if not m:
        return None
    try:
        return datetime.strptime(m.group(1), "%Y%m%d-%H%M%S")
    except ValueError:
        return None
