import sys

from shop.search import search

for product in search(" ".join(sys.argv[1:])):
    print(f"{product.sku}  {product.name} ({product.brand})  {product.price}")
