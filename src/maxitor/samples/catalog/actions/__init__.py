# src/maxitor/samples/catalog/actions/__init__.py
from maxitor.samples.catalog.actions.browse import BrowseCatalogAction, BrowseCatalogParams, BrowseCatalogResult
from maxitor.samples.catalog.actions.product_enrichment import (
    ProductEnrichmentAction,
    ProductEnrichmentParams,
    ProductEnrichmentResult,
)

__all__ = [
    "BrowseCatalogAction",
    "BrowseCatalogParams",
    "BrowseCatalogResult",
    "ProductEnrichmentAction",
    "ProductEnrichmentParams",
    "ProductEnrichmentResult",
]
