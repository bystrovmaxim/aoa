# src/maxitor/samples/catalog/__init__.py
"""
Каталог: SKU, обогащение, полный контур как у ``store``.

``dependencies``, ``resources``, ``plugins``, ``actions`` (browse + enrichment).
"""

from maxitor.samples.catalog.domain import CatalogDomain

__all__ = ["CatalogDomain"]
