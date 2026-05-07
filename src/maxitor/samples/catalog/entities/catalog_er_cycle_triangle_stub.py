# src/maxitor/samples/catalog/entities/catalog_er_cycle_triangle_stub.py
"""
Three ``BaseEntity`` rows wired as a directed 3-cycle A\u2192B\u2192C\u2192A (catalog domain).

Reverse arcs are mirrored with :class:`~action_machine.domain.relation_markers.Inverse`, so each
endpoint carries two reciprocal ``AssociationOne`` fields for readability in ERD tools.
One-way anchors into ``CatalogProductEntity`` / ``AcquisitionChannelLedgerEntity`` connect the triangle
into the broader catalog SKU and acquisition mesh.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, Inverse, Lifecycle, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.catalog.domain import CatalogDomain
from maxitor.samples.catalog.entities.catalog_acquisition_channel_ledger import AcquisitionChannelLedgerEntity
from maxitor.samples.catalog.entities.product_row import CatalogProductEntity


class _CatalogDirectedCycleSketchLifecycle(Lifecycle):
    _template = Lifecycle().state("open", "Open").to("settled").initial().state("settled", "Settled").final()


@entity(
    description="Catalog triangle vertex A (\u2192B, \u2190C reciprocal)",
    domain=CatalogDomain,
)
class CatalogDirectedCycleTriangleAEntity(BaseEntity):
    id: str = Field(description="Vertex A id")
    lifecycle: _CatalogDirectedCycleSketchLifecycle = Field(description="Sketch lifecycle")

    commercial_region_code: str = Field(description="Merchandising / pricing region discriminator")
    channel_partner_tag: str = Field(description="Acquisition partner or marketplace moniker")
    compliance_locale: str = Field(description="Regulatory storefront locale code")
    attribution_strategy: str = Field(description="Attribution-model key used for funnel credit")
    hash_stale_after_sec: int = Field(description="Seconds until cached facets must invalidate", ge=0)
    copy_variant_revision: int = Field(description="Narrative / SEO copy ordinal", ge=0)
    follow_b: Annotated[
        AssociationOne[CatalogDirectedCycleTriangleBEntity],
        Inverse(CatalogDirectedCycleTriangleBEntity, "back_from_a"),
    ] = Rel(description="Perimeter arc A\u2192B")  # type: ignore[assignment]

    back_from_c: Annotated[
        AssociationOne[CatalogDirectedCycleTriangleCEntity],
        Inverse(CatalogDirectedCycleTriangleCEntity, "follow_a"),
    ] = Rel(description="Closing arc C\u2192A (reciprocal pair)")  # type: ignore[assignment]

    anchor_product_row: Annotated[
        AssociationOne[CatalogProductEntity],
        NoInverse(),
    ] = Rel(description="Bridges vertex A into the primary catalog product table")  # type: ignore[assignment]


@entity(
    description="Catalog triangle vertex B (\u2190A / \u2192C reciprocal)",
    domain=CatalogDomain,
)
class CatalogDirectedCycleTriangleBEntity(BaseEntity):
    id: str = Field(description="Vertex B id")
    lifecycle: _CatalogDirectedCycleSketchLifecycle = Field(description="Sketch lifecycle")

    commercial_region_code: str = Field(description="Merchandising / pricing region discriminator")
    channel_partner_tag: str = Field(description="Acquisition partner or marketplace moniker")
    compliance_locale: str = Field(description="Regulatory storefront locale code")
    attribution_strategy: str = Field(description="Attribution-model key used for funnel credit")
    hash_stale_after_sec: int = Field(description="Seconds until cached facets must invalidate", ge=0)
    copy_variant_revision: int = Field(description="Narrative / SEO copy ordinal", ge=0)
    back_from_a: Annotated[
        AssociationOne[CatalogDirectedCycleTriangleAEntity],
        Inverse(CatalogDirectedCycleTriangleAEntity, "follow_b"),
    ] = Rel(description="Arc B\u2192A reciprocal")  # type: ignore[assignment]

    follow_c: Annotated[
        AssociationOne[CatalogDirectedCycleTriangleCEntity],
        Inverse(CatalogDirectedCycleTriangleCEntity, "back_from_b"),
    ] = Rel(description="Perimeter arc B\u2192C")  # type: ignore[assignment]

    anchor_acquisition_channel: Annotated[
        AssociationOne[AcquisitionChannelLedgerEntity],
        NoInverse(),
    ] = Rel(description="Bridges vertex B into acquisition-channel ledger stubs")  # type: ignore[assignment]


@entity(
    description="Catalog triangle vertex C (\u2190B / \u2192A reciprocal)",
    domain=CatalogDomain,
)
class CatalogDirectedCycleTriangleCEntity(BaseEntity):
    id: str = Field(description="Vertex C id")
    lifecycle: _CatalogDirectedCycleSketchLifecycle = Field(description="Sketch lifecycle")

    commercial_region_code: str = Field(description="Merchandising / pricing region discriminator")
    channel_partner_tag: str = Field(description="Acquisition partner or marketplace moniker")
    compliance_locale: str = Field(description="Regulatory storefront locale code")
    attribution_strategy: str = Field(description="Attribution-model key used for funnel credit")
    hash_stale_after_sec: int = Field(description="Seconds until cached facets must invalidate", ge=0)
    copy_variant_revision: int = Field(description="Narrative / SEO copy ordinal", ge=0)
    back_from_b: Annotated[
        AssociationOne[CatalogDirectedCycleTriangleBEntity],
        Inverse(CatalogDirectedCycleTriangleBEntity, "follow_c"),
    ] = Rel(description="Arc C\u2192B reciprocal")  # type: ignore[assignment]

    follow_a: Annotated[
        AssociationOne[CatalogDirectedCycleTriangleAEntity],
        Inverse(CatalogDirectedCycleTriangleAEntity, "back_from_c"),
    ] = Rel(description="Perimeter arc C\u2192A")  # type: ignore[assignment]


CatalogDirectedCycleTriangleAEntity.model_rebuild()
CatalogDirectedCycleTriangleBEntity.model_rebuild()
CatalogDirectedCycleTriangleCEntity.model_rebuild()
