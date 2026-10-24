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
