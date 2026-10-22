# packages/aoa-demo/src/aoa/demo/model/catalog/entities/catalog_touch_moment.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseCoreEntity, NoInverse, Rel
from aoa.action_machine.intents.entity import entity
from aoa.demo.model.catalog.domain import CatalogDomain
from aoa.demo.model.catalog.entities.catalog_acquisition_channel_ledger import AcquisitionChannelLedgerCoreEntity
from aoa.demo.model.catalog.entities.catalog_dense_lifecycle import CatalogDenseLifecycle
from aoa.demo.model.messaging.entities.msg_replay_ticket import ReplayTicketCoreEntity


@entity(description="Attributed touch moment", domain=CatalogDomain)
class TouchMomentCoreEntity(BaseCoreEntity):
    id: str = Field(description="Touch id")
    lifecycle: CatalogDenseLifecycle = Field(description="Touch lifecycle")

    commercial_region_code: str = Field(description="Merchandising / pricing region discriminator")
    channel_partner_tag: str = Field(description="Acquisition partner or marketplace moniker")
    compliance_locale: str = Field(description="Regulatory storefront locale code")
    attribution_strategy: str = Field(description="Attribution-model key used for funnel credit")
    hash_stale_after_sec: int = Field(description="Seconds until cached facets must invalidate", ge=0)
    copy_variant_revision: int = Field(description="Narrative / SEO copy ordinal", ge=0)
    channel_ledger: Annotated[
        AssociationOne[AcquisitionChannelLedgerCoreEntity],
        NoInverse(),
    ] = Rel(
        description="Acquisition ledger segment"
    )  # type: ignore[assignment]

    replay_ticket: Annotated[
        AssociationOne[ReplayTicketCoreEntity],
        NoInverse(),
    ] = Rel(
        description="Messaging replay ticket for deterministic touch lineage"
    )  # type: ignore[assignment]


TouchMomentCoreEntity.model_rebuild()
