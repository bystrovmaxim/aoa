# packages/aoa-maxitor/src/aoa/maxitor/samples/catalog/__init__.py
"""
Catalog: SKU, enrichment, same end-to-end shape as ``store``.

``dependencies``, ``resources``, ``plugins``, ``actions`` (browse + enrichment).
"""

from aoa.maxitor.samples.catalog.domain import CatalogDomain

__all__ = ["CatalogDomain"]
