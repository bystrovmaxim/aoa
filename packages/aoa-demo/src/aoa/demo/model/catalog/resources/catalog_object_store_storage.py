# packages/aoa-demo/src/aoa/demo/model/catalog/resources/catalog_object_store_storage.py
"""
CatalogObjectStoreStorage — database-free demo storage with SQL lifecycle semantics.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Represent the domain's storage in the demo without opening a database connection.
The SQL lifecycle methods are harmless no-ops; inherited close remains safe.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    Domain actions and entities -> CatalogObjectStoreStorage -> SqlStorage contract
"""

from aoa.action_machine.intents.entities import entities
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.sql import SqlStorage
from aoa.demo.model.catalog.entities.catalog_acquisition_channel_ledger import AcquisitionChannelLedgerCoreEntity
from aoa.demo.model.catalog.entities.catalog_audience_segment_glue import AudienceSegmentGlueCoreEntity
from aoa.demo.model.catalog.entities.catalog_bridge_price_acquisition import CatalogPriceAcquisitionLinkCoreEntity
from aoa.demo.model.catalog.entities.catalog_bridge_shelf_bundle import CatalogShelfBundleLinkCoreEntity
from aoa.demo.model.catalog.entities.catalog_bundle_cardinality_rule import BundleCardinalityRuleCoreEntity
from aoa.demo.model.catalog.entities.catalog_conversion_attribution_stub import ConversionAttributionStubCoreEntity
from aoa.demo.model.catalog.entities.catalog_er_cycle_triangle_stub import (
    CatalogDirectedCycleTriangleACoreEntity,
    CatalogDirectedCycleTriangleBCoreEntity,
    CatalogDirectedCycleTriangleCCoreEntity,
)
from aoa.demo.model.catalog.entities.catalog_merch_copy_variant import MerchCopyVariantCoreEntity
from aoa.demo.model.catalog.entities.catalog_price_ribbon_snapshot import PriceRibbonSnapshotCoreEntity
from aoa.demo.model.catalog.entities.catalog_product_review import ProductReviewCoreEntity
from aoa.demo.model.catalog.entities.catalog_regulatory_label_pack import RegulatoryLabelPackCoreEntity
from aoa.demo.model.catalog.entities.catalog_shelf_placement_hint import ShelfPlacementHintCoreEntity
from aoa.demo.model.catalog.entities.catalog_touch_moment import TouchMomentCoreEntity
from aoa.demo.model.catalog.entities.product_row import CatalogProductCoreEntity


@meta(description="Media/object store for catalog (stub)")
@entities(
    AcquisitionChannelLedgerCoreEntity,
    AudienceSegmentGlueCoreEntity,
    CatalogPriceAcquisitionLinkCoreEntity,
    CatalogShelfBundleLinkCoreEntity,
    BundleCardinalityRuleCoreEntity,
    ConversionAttributionStubCoreEntity,
    CatalogDirectedCycleTriangleACoreEntity,
    CatalogDirectedCycleTriangleBCoreEntity,
    CatalogDirectedCycleTriangleCCoreEntity,
    MerchCopyVariantCoreEntity,
    PriceRibbonSnapshotCoreEntity,
    ProductReviewCoreEntity,
    RegulatoryLabelPackCoreEntity,
    ShelfPlacementHintCoreEntity,
    TouchMomentCoreEntity,
    CatalogProductCoreEntity,
)
class CatalogObjectStoreStorage(SqlStorage):
    """
    AI-CORE-BEGIN
    ROLE: Database-free storage for the demo domain.
    CONTRACT: Provide the SQL lifecycle without acquiring a connection.
    INVARIANTS: The class retains its Storage kind and domain metadata.
    AI-CORE-END
    """

    def __init__(self, rollup: bool = False) -> None:
        """Preserve the SQL contract’s rollup configuration."""
        super().__init__(rollup=rollup)

    async def open(self) -> None:
        """Keep the database-free store ready for use."""
        return None

    async def begin(self) -> None:
        """Accept a transaction boundary without external state."""
        return None

    async def commit(self) -> None:
        """Finish the demo transaction without persistence."""
        return None

    async def rollback(self) -> None:
        """Finish the demo transaction without external writes."""
        return None
