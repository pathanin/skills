import csv
import unicodedata
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path


@dataclass(frozen=True)
class Product:
    sku: str
    name: str
    brand: str
    category: str
    price: Decimal
    popularity: int
    search_text: str


def normalize(text: str) -> str:
    """Lower-case, strip accents and collapse whitespace so 'Café  Crème' matches 'cafe creme'."""
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return " ".join(stripped.casefold().split())


_cache: dict[Path, tuple[float, list[Product]]] = {}


def get_catalog(path: Path) -> list[Product]:
    """Parsed catalog, re-read only when the file changes on disk."""
    mtime = Path(path).stat().st_mtime
    cached = _cache.get(path)
    if cached is None or cached[0] != mtime:
        cached = (mtime, load_catalog(path))
        _cache[path] = cached
    return cached[1]


def load_catalog(path: Path) -> list[Product]:
    products = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            products.append(Product(
                sku=row["sku"],
                name=row["name"],
                brand=row["brand"],
                category=row["category"],
                price=Decimal(row["price"]),
                popularity=int(row["popularity"] or 0),
                search_text=normalize(f"{row['name']} {row['brand']} {row['category']}"),
            ))
    return products
