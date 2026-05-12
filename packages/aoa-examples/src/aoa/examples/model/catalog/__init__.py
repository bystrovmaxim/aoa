# packages/aoa-examples/src/aoa/examples/model/catalog/__init__.py
"""
Catalog: SKU, enrichment, same end-to-end shape as ``store``.

``dependencies``, ``resources``, ``plugins``, ``actions`` (browse + enrichment).
"""

from aoa.examples.model.catalog.domain import CatalogDomain

__all__ = ["CatalogDomain"]
