# src/maxitor/samples/store/entities/audit_log_entry.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.store.domain import StoreDomain
from maxitor.samples.store.entities.lifecycle import AuditLogEntryLifecycle
from maxitor.samples.store.entities.sales_core import SalesOrderEntity


@entity(description="Immutable audit row", domain=StoreDomain)
class AuditLogEntryEntity(BaseEntity):
    id: str = Field(description="Audit id")
    lifecycle: AuditLogEntryLifecycle = Field(description="Audit entry lifecycle")
    action_performed: str = Field(description="Action label")
    actor_id: str = Field(description="Actor id")

    storefront_channel: str = Field(description="POS / kiosk / ecommerce channel moniker")
    compliance_rating: str = Field(description="Fraud / AML posture snapshot")
    fulfillment_priority: int = Field(description="Relative orchestration priority ordinal", ge=0)
    tax_jurisdiction_stub: str = Field(description="Derived routing hint for taxation engines")
    target_order: Annotated[
        AssociationOne[SalesOrderEntity],
        NoInverse(),
    ] = Rel(description="Related order")  # type: ignore[assignment]


AuditLogEntryEntity.model_rebuild()
