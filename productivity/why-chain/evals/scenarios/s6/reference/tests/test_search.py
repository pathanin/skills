import pytest

from shop import config
from shop.api import handle_search
from shop.catalog import normalize
from shop.search import search

CATALOG = """sku,name,brand,category,price,popularity
A1,Blue Enamel Mug,Fjällräven,Kitchen,14.00,812
A2,Travel Mug Steel,Müller,Kitchen,24.00,1290
A3,Café Crème Cup,Café Bleu,Kitchen,9.00,50
A4,Blue Steel Pan,Lodge,Cookware,45.00,2210
"""


@pytest.fixture(autouse=True)
def small_catalog(tmp_path, monkeypatch):
    path = tmp_path / "catalog.csv"
    path.write_text(CATALOG, encoding="utf-8")
    monkeypatch.setattr(config, "CATALOG_PATH", path)


def test_normalize_strips_accents_and_case():
    assert normalize("  Café   CRÈME ") == "cafe creme"


def test_all_terms_must_match_ranked_by_popularity():
    assert [p.sku for p in search("blue")] == ["A4", "A1"]
    assert [p.sku for p in search("blue mug")] == ["A1"]


def test_accent_insensitive_on_both_sides():
    assert [p.sku for p in search("cafe")] == ["A3"]
    assert [p.sku for p in search("müller")] == ["A2"]
    assert [p.sku for p in search("MULLER")] == ["A2"]


def test_limit_and_empty_query():
    assert len(search("kitchen", limit=2)) == 2
    assert search("   ") == []


def test_api_shapes_response():
    status, body = handle_search("q=steel&limit=5")
    assert status == 200
    assert [r["sku"] for r in body["results"]] == ["A4", "A2"]
    assert handle_search("q=")[0] == 400
