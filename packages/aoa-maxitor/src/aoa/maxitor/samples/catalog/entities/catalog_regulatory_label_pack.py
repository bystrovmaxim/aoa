# packages/aoa-maxitor/src/aoa/maxitor/samples/catalog/entities/catalog_regulatory_label_pack.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from aoa.action_machine.intents.entity import entity
from aoa.maxitor.samples.catalog.domain import CatalogDomain
from aoa.maxitor.samples.catalog.entities.catalog_dense_lifecycle import CatalogDenseLifecycle
from aoa.maxitor.samples.catalog.entities.catalog_merch_copy_variant import MerchCopyVariantEntity


@entity(description="Regulatory label continuation of planogram / copy spine", domain=CatalogDomain)
class RegulatoryLabelPackEntity(BaseEntity):
    id: str = Field(description="Pack id")
    lifecycle: CatalogDenseLifecycle = Field(description="Regulatory pack lifecycle")

    commercial_region_code: str = Field(description="Merchandising / pricing region discriminator")
    channel_partner_tag: str = Field(description="Acquisition partner or marketplace moniker")
    compliance_locale: str = Field(description="Regulatory storefront locale code")
    attribution_strategy: str = Field(description="Attribution-model key used for funnel credit")
    hash_stale_after_sec: int = Field(description="Seconds until cached facets must invalidate", ge=0)
    copy_variant_revision: int = Field(description="Narrative / SEO copy ordinal", ge=0)
    merch_copy: Annotated[
        AssociationOne[MerchCopyVariantEntity],
        NoInverse(),
    ] = Rel(description="Parent merch variant row")  # type: ignore[assignment]


RegulatoryLabelPackEntity.model_rebuild()
