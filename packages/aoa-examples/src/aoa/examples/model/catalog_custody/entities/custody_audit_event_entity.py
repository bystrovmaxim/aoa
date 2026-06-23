# packages/aoa-examples/src/aoa/examples/model/catalog_custody/entities/custody_audit_event_entity.py
"""Immutable custody audit envelope pointing at a regulated SKU row."""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from aoa.action_machine.intents.entity import entity
from aoa.examples.model.catalog_custody.catalog_custody_domain import CatalogCustodyDomain
from aoa.examples.model.catalog_custody.entities.regulated_stock_keeping_unit_row_entity import (
    RegulatedStockKeepingUnitRowEntity,
)


@entity(description="Append-only custody audit artifact tied to a SKU anchor", domain=CatalogCustodyDomain)
class CustodyAuditEventEntity(BaseEntity):
    event_id: str = Field(description="Audit envelope id")
    actor_ref: str = Field(description="Originating custody actor ref")
    event_kind: str = Field(description="peek | inspect_attest | reconcile | pulse")
    subject_sku_row: Annotated[
        AssociationOne[RegulatedStockKeepingUnitRowEntity],
        NoInverse(),
    ] = Rel(
        description="Regulated SKU row this audit references"
    )  # type: ignore[assignment]
