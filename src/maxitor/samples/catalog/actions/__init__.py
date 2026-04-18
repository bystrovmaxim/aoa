# src/maxitor/samples/catalog/actions/__init__.py
from maxitor.samples.catalog.actions.browse import BrowseCatalogAction
from maxitor.samples.catalog.actions.category_list import CategoryListAction
from maxitor.samples.catalog.actions.import_sku_stub import ImportSkuStubAction
from maxitor.samples.catalog.actions.price_snapshot import PriceSnapshotAction
from maxitor.samples.catalog.actions.product_enrichment import ProductEnrichmentAction

BrowseCatalogParams = BrowseCatalogAction.Params
BrowseCatalogResult = BrowseCatalogAction.Result
CategoryListParams = CategoryListAction.Params
CategoryListResult = CategoryListAction.Result
ImportSkuStubParams = ImportSkuStubAction.Params
ImportSkuStubResult = ImportSkuStubAction.Result
PriceSnapshotParams = PriceSnapshotAction.Params
PriceSnapshotResult = PriceSnapshotAction.Result
ProductEnrichmentParams = ProductEnrichmentAction.Params
ProductEnrichmentResult = ProductEnrichmentAction.Result

__all__ = [
    "BrowseCatalogAction",
    "BrowseCatalogParams",
    "BrowseCatalogResult",
    "CategoryListAction",
    "CategoryListParams",
    "CategoryListResult",
    "ImportSkuStubAction",
    "ImportSkuStubParams",
    "ImportSkuStubResult",
    "PriceSnapshotAction",
    "PriceSnapshotParams",
    "PriceSnapshotResult",
    "ProductEnrichmentAction",
    "ProductEnrichmentParams",
    "ProductEnrichmentResult",
]
