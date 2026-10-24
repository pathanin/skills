from urllib.parse import parse_qs

from shop.search import search


def handle_search(query_string: str) -> tuple[int, dict]:
    params = parse_qs(query_string)
    q = params.get("q", [""])[0].strip()
    if not q:
        return 400, {"error": "missing q"}
    try:
        limit = min(int(params.get("limit", ["20"])[0]), 100)
    except ValueError:
        return 400, {"error": "bad limit"}
    results = search(q, limit=limit)
    return 200, {
        "query": q,
        "results": [
            {"sku": p.sku, "name": p.name, "brand": p.brand, "price": str(p.price)}
            for p in results
        ],
    }
