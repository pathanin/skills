import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = Path(os.environ.get("SHOP_CATALOG_PATH", ROOT / "data" / "catalog.csv"))
DEFAULT_LIMIT = 20
