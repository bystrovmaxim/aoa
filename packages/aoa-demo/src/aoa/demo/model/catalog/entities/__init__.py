# packages/aoa-demo/src/aoa/demo/model/catalog/entities/__init__.py
from __future__ import annotations

from aoa.demo.model.catalog.entities.catalog_acquisition_channel_ledger import AcquisitionChannelLedgerCoreEntity
from aoa.demo.model.catalog.entities.catalog_audience_segment_glue import AudienceSegmentGlueCoreEntity
from aoa.demo.model.catalog.entities.catalog_availability_projection import AvailabilityProjectionCoreEntity
from aoa.demo.model.catalog.entities.catalog_bridge_price_acquisition import CatalogPriceAcquisitionLinkCoreEntity
from aoa.demo.model.catalog.entities.catalog_bridge_shelf_bundle import CatalogShelfBundleLinkCoreEntity
from aoa.demo.model.catalog.entities.catalog_bundle_cardinality_rule import BundleCardinalityRuleCoreEntity
from aoa.demo.model.catalog.entities.catalog_conversion_attribution_stub import ConversionAttributionStubCoreEntity
from aoa.demo.model.catalog.entities.catalog_dense_lifecycle import CatalogDenseLifecycle
from aoa.demo.model.catalog.entities.catalog_er_cycle_triangle_stub import (
    CatalogDirectedCycleTriangleACoreEntity,
    CatalogDirectedCycleTriangleBCoreEntity,
    CatalogDirectedCycleTriangleCCoreEntity,
)
from aoa.demo.model.catalog.entities.catalog_merch_copy_variant import MerchCopyVariantCoreEntity
from aoa.demo.model.catalog.entities.catalog_price_ribbon_snapshot import PriceRibbonSnapshotCoreEntity
from aoa.demo.model.catalog.entities.catalog_product_lifecycle import CatalogProductLifecycle
from aoa.demo.model.catalog.entities.catalog_regulatory_label_pack import RegulatoryLabelPackCoreEntity
from aoa.demo.model.catalog.entities.catalog_search_boost_weight import SearchBoostWeightCoreEntity
from aoa.demo.model.catalog.entities.catalog_shelf_placement_hint import ShelfPlacementHintCoreEntity
from aoa.demo.model.catalog.entities.catalog_touch_moment import TouchMomentCoreEntity
from aoa.demo.model.catalog.entities.product_row import CatalogProductCoreEntity

__all__ = [
    "AcquisitionChannelLedgerCoreEntity",
    "AudienceSegmentGlueCoreEntity",
    "AvailabilityProjectionCoreEntity",
    "BundleCardinalityRuleCoreEntity",
    "CatalogDenseLifecycle",
    "CatalogDirectedCycleTriangleACoreEntity",
    "CatalogDirectedCycleTriangleBCoreEntity",
    "CatalogDirectedCycleTriangleCCoreEntity",
    "CatalogPriceAcquisitionLinkCoreEntity",
    "CatalogProductCoreEntity",
    "CatalogProductLifecycle",
    "CatalogShelfBundleLinkCoreEntity",
    "ConversionAttributionStubCoreEntity",
    "MerchCopyVariantCoreEntity",
    "PriceRibbonSnapshotCoreEntity",
    "RegulatoryLabelPackCoreEntity",
    "SearchBoostWeightCoreEntity",
    "ShelfPlacementHintCoreEntity",
    "TouchMomentCoreEntity",
]
