# packages/aoa-demo/src/aoa/demo/model/catalog/entities/catalog_er_cycle_triangle_stub.py
"""
Three ``BaseEntity`` rows wired as a directed 3-cycle A\u2192B\u2192C\u2192A (catalog domain).

Reverse arcs are mirrored with :class:`~aoa.action_machine.domain.relation_markers.Inverse`, so each
endpoint carries two reciprocal ``AssociationOne`` fields for readability in ERD tools.
One-way anchors into ``CatalogProductCoreEntity`` / ``AcquisitionChannelLedgerCoreEntity`` connect the triangle
into the broader catalog SKU and acquisition mesh.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import (
    AssociationOne,
    BaseCoreEntity,
    BaseStateEntity,
    Inverse,
    Lifecycle,
    NoInverse,
    Rel,
    value,
)
from aoa.action_machine.intents.entity import entity
from aoa.demo.model.catalog.domain import CatalogDomain
from aoa.demo.model.catalog.entities.catalog_acquisition_channel_ledger import AcquisitionChannelLedgerCoreEntity
from aoa.demo.model.catalog.entities.product_row import CatalogProductCoreEntity


class _CatalogDirectedCycleSketchStateEntity(BaseStateEntity):
    """Status of the _CatalogDirectedCycleSketch axis."""

    sort_order: int = Field(default=0, description="Presentation order")

    OPEN = value(code="open", display_name="Open", sort_order=1)
    SETTLED = value(code="settled", display_name="Settled", sort_order=2)



class _CatalogDirectedCycleSketchLifecycle(Lifecycle[_CatalogDirectedCycleSketchStateEntity]):
    """Statuses and links of the _CatalogDirectedCycleSketchLifecycle axis."""


    _template = Lifecycle().state(_CatalogDirectedCycleSketchStateEntity.OPEN).to(_CatalogDirectedCycleSketchStateEntity.SETTLED).initial().state(_CatalogDirectedCycleSketchStateEntity.SETTLED).final()


@entity(
    description="Catalog triangle vertex A (\u2192B, \u2190C reciprocal)",
    domain=CatalogDomain,
)
class CatalogDirectedCycleTriangleACoreEntity(BaseCoreEntity):
    id: str = Field(description="Vertex A id")
    lifecycle: _CatalogDirectedCycleSketchLifecycle = Field(description="Sketch lifecycle")

    commercial_region_code: str = Field(description="Merchandising / pricing region discriminator")
    channel_partner_tag: str = Field(description="Acquisition partner or marketplace moniker")
    compliance_locale: str = Field(description="Regulatory storefront locale code")
    attribution_strategy: str = Field(description="Attribution-model key used for funnel credit")
    hash_stale_after_sec: int = Field(description="Seconds until cached facets must invalidate", ge=0)
    copy_variant_revision: int = Field(description="Narrative / SEO copy ordinal", ge=0)
    follow_b: Annotated[
        AssociationOne[CatalogDirectedCycleTriangleBCoreEntity],
        Inverse(CatalogDirectedCycleTriangleBCoreEntity, "back_from_a"),
    ] = Rel(
        description="Perimeter arc A\u2192B"
    )  # type: ignore[assignment]

    back_from_c: Annotated[
        AssociationOne[CatalogDirectedCycleTriangleCCoreEntity],
        Inverse(CatalogDirectedCycleTriangleCCoreEntity, "follow_a"),
    ] = Rel(
        description="Closing arc C\u2192A (reciprocal pair)"
    )  # type: ignore[assignment]

    anchor_product_row: Annotated[
        AssociationOne[CatalogProductCoreEntity],
        NoInverse(),
    ] = Rel(
        description="Bridges vertex A into the primary catalog product table"
    )  # type: ignore[assignment]


@entity(
    description="Catalog triangle vertex B (\u2190A / \u2192C reciprocal)",
    domain=CatalogDomain,
)
class CatalogDirectedCycleTriangleBCoreEntity(BaseCoreEntity):
    id: str = Field(description="Vertex B id")
    lifecycle: _CatalogDirectedCycleSketchLifecycle = Field(description="Sketch lifecycle")

    commercial_region_code: str = Field(description="Merchandising / pricing region discriminator")
    channel_partner_tag: str = Field(description="Acquisition partner or marketplace moniker")
    compliance_locale: str = Field(description="Regulatory storefront locale code")
    attribution_strategy: str = Field(description="Attribution-model key used for funnel credit")
    hash_stale_after_sec: int = Field(description="Seconds until cached facets must invalidate", ge=0)
    copy_variant_revision: int = Field(description="Narrative / SEO copy ordinal", ge=0)
    back_from_a: Annotated[
        AssociationOne[CatalogDirectedCycleTriangleACoreEntity],
        Inverse(CatalogDirectedCycleTriangleACoreEntity, "follow_b"),
    ] = Rel(
        description="Arc B\u2192A reciprocal"
    )  # type: ignore[assignment]

    follow_c: Annotated[
        AssociationOne[CatalogDirectedCycleTriangleCCoreEntity],
        Inverse(CatalogDirectedCycleTriangleCCoreEntity, "back_from_b"),
    ] = Rel(
        description="Perimeter arc B\u2192C"
    )  # type: ignore[assignment]

    anchor_acquisition_channel: Annotated[
        AssociationOne[AcquisitionChannelLedgerCoreEntity],
        NoInverse(),
    ] = Rel(
        description="Bridges vertex B into acquisition-channel ledger stubs"
    )  # type: ignore[assignment]


@entity(
    description="Catalog triangle vertex C (\u2190B / \u2192A reciprocal)",
    domain=CatalogDomain,
)
class CatalogDirectedCycleTriangleCCoreEntity(BaseCoreEntity):
    id: str = Field(description="Vertex C id")
    lifecycle: _CatalogDirectedCycleSketchLifecycle = Field(description="Sketch lifecycle")

    commercial_region_code: str = Field(description="Merchandising / pricing region discriminator")
    channel_partner_tag: str = Field(description="Acquisition partner or marketplace moniker")
    compliance_locale: str = Field(description="Regulatory storefront locale code")
    attribution_strategy: str = Field(description="Attribution-model key used for funnel credit")
    hash_stale_after_sec: int = Field(description="Seconds until cached facets must invalidate", ge=0)
    copy_variant_revision: int = Field(description="Narrative / SEO copy ordinal", ge=0)
    back_from_b: Annotated[
        AssociationOne[CatalogDirectedCycleTriangleBCoreEntity],
        Inverse(CatalogDirectedCycleTriangleBCoreEntity, "follow_c"),
    ] = Rel(
        description="Arc C\u2192B reciprocal"
    )  # type: ignore[assignment]

    follow_a: Annotated[
        AssociationOne[CatalogDirectedCycleTriangleACoreEntity],
        Inverse(CatalogDirectedCycleTriangleACoreEntity, "back_from_c"),
    ] = Rel(
        description="Perimeter arc C\u2192A"
    )  # type: ignore[assignment]


CatalogDirectedCycleTriangleACoreEntity.model_rebuild()
CatalogDirectedCycleTriangleBCoreEntity.model_rebuild()
CatalogDirectedCycleTriangleCCoreEntity.model_rebuild()
