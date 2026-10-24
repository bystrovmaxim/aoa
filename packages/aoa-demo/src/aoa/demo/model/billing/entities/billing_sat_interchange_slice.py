# packages/aoa-demo/src/aoa/demo/model/billing/entities/billing_sat_interchange_slice.py
"""Standalone interchange economics root row."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseCoreEntity, NoInverse
from aoa.action_machine.intents.entity import entity
from aoa.demo.model.billing.domain import BillingDomain
from aoa.demo.model.billing.entities.billing_dense_lifecycle import BillingDenseLifecycle
from aoa.demo.model.dictionaries.entities.currency_enum import CurrencyEnumEntity

if TYPE_CHECKING:
    from aoa.demo.model.billing.entities.billing_mesh_chargeback_ingest import (
        BillingChargebackIngestCorrelateCoreEntity,
    )


@entity(description="Interchange economics slice", domain=BillingDomain)
class InterchangeAssessmentSliceCoreEntity(BaseCoreEntity):
    id: str = Field(description="Slice id")
    lifecycle: BillingDenseLifecycle = Field(description="Interchange slice lifecycle")

    scheme_code: str = Field(description="Interchange program / scheme code")
    assessor_build: str = Field(description="Tariff engine build id")
    ic_plus_basis_points: int = Field(description="IC++ component in basis points", ge=0)
    network_batch_id: str = Field(description="Network settlement batch marker")

    legal_entity_ref: str = Field(description="Debtor / posting-company anchor")
    currency_iso: Annotated[AssociationOne[CurrencyEnumEntity], NoInverse()] = Field(description="Declared ISO-4217 money unit")
    chargeback_ingest_correlate: Annotated[
        AssociationOne[BillingChargebackIngestCorrelateCoreEntity],
        NoInverse(),
    ] = Field(
        description="Correlate row linking dispute artefacts to ingest manifests",
    )
