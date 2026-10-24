import time

from shop import config
from shop.catalog import Product, load_catalog, normalize


_CACHE: dict = {}
TTL_SECONDS = 300


def _catalog(path):
    hit = _CACHE.get(path)
    now = time.monotonic()
    if hit is None or now - hit[0] > TTL_SECONDS:
        hit = (now, load_catalog(path))
        _CACHE[path] = hit
    return hit[1]


def search(query: str, limit: int = config.DEFAULT_LIMIT) -> list[Product]:
    terms = normalize(query).split()
    if not terms:
        return []
    products = _catalog(config.CATALOG_PATH)
    hits = [p for p in products if all(term in p.search_text for term in terms)]
    hits.sort(key=lambda p: (-p.popularity, p.name))
    return hits[:limit]
