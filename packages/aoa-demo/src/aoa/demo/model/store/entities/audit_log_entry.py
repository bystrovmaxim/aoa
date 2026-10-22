# packages/aoa-demo/src/aoa/demo/model/store/entities/audit_log_entry.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseDetailEntity, NoInverse, Rel
from aoa.action_machine.intents.entity import entity
from aoa.demo.model.store.entities.audit_log_entry_lifecycle import AuditLogEntryLifecycle
from aoa.demo.model.store.entities.sales_core import SalesOrderCoreEntity
from aoa.demo.model.store.store_domain import StoreDomain


@entity(description="Immutable audit row", domain=StoreDomain)
class AuditLogEntryDetailEntity(BaseDetailEntity):
    id: str = Field(description="Audit id")
    lifecycle: AuditLogEntryLifecycle = Field(description="Audit entry lifecycle")
    action_performed: str = Field(description="Action label")
    actor_id: str = Field(description="Actor id")

    storefront_channel: str = Field(description="POS / kiosk / ecommerce channel moniker")
    compliance_rating: str = Field(description="Fraud / AML posture snapshot")
    fulfillment_priority: int = Field(description="Relative orchestration priority ordinal", ge=0)
    tax_jurisdiction_stub: str = Field(description="Derived routing hint for taxation engines")
    target_order: Annotated[
        AssociationOne[SalesOrderCoreEntity],
        NoInverse(),
    ] = Rel(
        description="Related order"
    )  # type: ignore[assignment]


AuditLogEntryDetailEntity.model_rebuild()
