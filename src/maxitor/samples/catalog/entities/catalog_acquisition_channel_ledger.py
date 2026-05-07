# src/maxitor/samples/catalog/entities/catalog_acquisition_channel_ledger.py
from __future__ import annotations

from pydantic import Field

from action_machine.domain import BaseEntity
from action_machine.intents.entity import entity
from maxitor.samples.catalog.domain import CatalogDomain
from maxitor.samples.catalog.entities.catalog_dense_lifecycle import CatalogDenseLifecycle


@entity(description="Acquisition channel attribution ledger head", domain=CatalogDomain)
class AcquisitionChannelLedgerEntity(BaseEntity):
    id: str = Field(description="Ledger id")
    lifecycle: CatalogDenseLifecycle = Field(description="Channel ledger lifecycle")

    commercial_region_code: str = Field(description="Merchandising / pricing region discriminator")
    channel_partner_tag: str = Field(description="Acquisition partner or marketplace moniker")
    compliance_locale: str = Field(description="Regulatory storefront locale code")
    attribution_strategy: str = Field(description="Attribution-model key used for funnel credit")
    hash_stale_after_sec: int = Field(description="Seconds until cached facets must invalidate", ge=0)
    copy_variant_revision: int = Field(description="Narrative / SEO copy ordinal", ge=0)


AcquisitionChannelLedgerEntity.model_rebuild()
