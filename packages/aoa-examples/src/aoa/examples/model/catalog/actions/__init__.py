# packages/aoa-examples/src/aoa/examples/model/catalog/actions/__init__.py
from aoa.examples.model.catalog.actions.browse import BrowseCatalogAction
from aoa.examples.model.catalog.actions.category_list import CategoryListAction
from aoa.examples.model.catalog.actions.import_sku_stub import ImportSkuStubAction
from aoa.examples.model.catalog.actions.price_snapshot import PriceSnapshotAction
from aoa.examples.model.catalog.actions.product_enrichment import ProductEnrichmentAction

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
