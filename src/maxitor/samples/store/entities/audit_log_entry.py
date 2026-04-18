# src/maxitor/samples/store/entities/audit_log_entry.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel, entity
from maxitor.samples.store.domain import StoreDomain
from maxitor.samples.store.entities.sales_core import SalesOrderEntity


@entity(description="Immutable audit row", domain=StoreDomain)
class AuditLogEntryEntity(BaseEntity):
    id: str = Field(description="Audit id")
    action_performed: str = Field(description="Action label")
    actor_id: str = Field(description="Actor id")

    target_order: Annotated[
        AssociationOne[SalesOrderEntity],
        NoInverse(),
    ] = Rel(description="Related order")  # type: ignore[assignment]
