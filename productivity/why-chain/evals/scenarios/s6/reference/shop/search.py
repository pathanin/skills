from shop import config
from shop.catalog import Product, get_catalog, normalize


def search(query: str, limit: int = config.DEFAULT_LIMIT) -> list[Product]:
    terms = normalize(query).split()
    if not terms:
        return []
    products = get_catalog(config.CATALOG_PATH)
    hits = [p for p in products if all(term in p.search_text for term in terms)]
    hits.sort(key=lambda p: (-p.popularity, p.name))
    return hits[:limit]
