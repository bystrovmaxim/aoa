# src/src/maxitor/samples/catalog/entities/__init__.py
from __future__ import annotations

from maxitor.samples.catalog.entities.catalog_acquisition_channel_ledger import AcquisitionChannelLedgerEntity
from maxitor.samples.catalog.entities.catalog_audience_segment_glue import AudienceSegmentGlueEntity
from maxitor.samples.catalog.entities.catalog_availability_projection import AvailabilityProjectionEntity
from maxitor.samples.catalog.entities.catalog_bridge_price_acquisition import CatalogPriceAcquisitionLinkEntity
from maxitor.samples.catalog.entities.catalog_bridge_shelf_bundle import CatalogShelfBundleLinkEntity
from maxitor.samples.catalog.entities.catalog_bundle_cardinality_rule import BundleCardinalityRuleEntity
from maxitor.samples.catalog.entities.catalog_conversion_attribution_stub import ConversionAttributionStubEntity
from maxitor.samples.catalog.entities.catalog_dense_lifecycle import CatalogDenseLifecycle
from maxitor.samples.catalog.entities.catalog_merch_copy_variant import MerchCopyVariantEntity
from maxitor.samples.catalog.entities.catalog_price_ribbon_snapshot import PriceRibbonSnapshotEntity
from maxitor.samples.catalog.entities.catalog_product_lifecycle import CatalogProductLifecycle
from maxitor.samples.catalog.entities.catalog_regulatory_label_pack import RegulatoryLabelPackEntity
from maxitor.samples.catalog.entities.catalog_search_boost_weight import SearchBoostWeightEntity
from maxitor.samples.catalog.entities.catalog_shelf_placement_hint import ShelfPlacementHintEntity
from maxitor.samples.catalog.entities.catalog_touch_moment import TouchMomentEntity
from maxitor.samples.catalog.entities.product_row import CatalogProductEntity

__all__ = [
    "AcquisitionChannelLedgerEntity",
    "AudienceSegmentGlueEntity",
    "AvailabilityProjectionEntity",
    "BundleCardinalityRuleEntity",
    "CatalogDenseLifecycle",
    "CatalogPriceAcquisitionLinkEntity",
    "CatalogProductEntity",
    "CatalogProductLifecycle",
    "CatalogShelfBundleLinkEntity",
    "ConversionAttributionStubEntity",
    "MerchCopyVariantEntity",
    "PriceRibbonSnapshotEntity",
    "RegulatoryLabelPackEntity",
    "SearchBoostWeightEntity",
    "ShelfPlacementHintEntity",
    "TouchMomentEntity",
]
