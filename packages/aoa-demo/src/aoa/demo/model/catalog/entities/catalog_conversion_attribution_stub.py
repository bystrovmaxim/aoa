# packages/aoa-demo/src/aoa/demo/model/catalog/entities/catalog_conversion_attribution_stub.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseCoreEntity, NoInverse
from aoa.action_machine.intents.entity import entity
from aoa.demo.model.catalog.domain import CatalogDomain
from aoa.demo.model.catalog.entities.catalog_dense_lifecycle import CatalogDenseLifecycle
from aoa.demo.model.catalog.entities.catalog_touch_moment import TouchMomentCoreEntity


@entity(description="Conversion attribution stub chained from touch moment", domain=CatalogDomain)
class ConversionAttributionStubCoreEntity(BaseCoreEntity):
    id: str = Field(description="Stub id")
    lifecycle: CatalogDenseLifecycle = Field(description="Conversion stub lifecycle")

    commercial_region_code: str = Field(description="Merchandising / pricing region discriminator")
    channel_partner_tag: str = Field(description="Acquisition partner or marketplace moniker")
    compliance_locale: str = Field(description="Regulatory storefront locale code")
    attribution_strategy: str = Field(description="Attribution-model key used for funnel credit")
    hash_stale_after_sec: int = Field(description="Seconds until cached facets must invalidate", ge=0)
    copy_variant_revision: int = Field(description="Narrative / SEO copy ordinal", ge=0)
    touch: Annotated[
        AssociationOne[TouchMomentCoreEntity],
        NoInverse(),
    ] = Field(
        description="Last touch linkage"
    )


ConversionAttributionStubCoreEntity.model_rebuild()
