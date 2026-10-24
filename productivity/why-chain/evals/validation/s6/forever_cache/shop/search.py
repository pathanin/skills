from functools import lru_cache

from shop import config
from shop.catalog import Product, load_catalog, normalize


def search(query: str, limit: int = config.DEFAULT_LIMIT) -> list[Product]:
    terms = normalize(query).split()
    if not terms:
        return []
    products = _cached_catalog(config.CATALOG_PATH)
    hits = [p for p in products if all(term in p.search_text for term in terms)]
    hits.sort(key=lambda p: (-p.popularity, p.name))
    return hits[:limit]


@lru_cache(maxsize=4)
def _cached_catalog(path):
    return load_catalog(path)
