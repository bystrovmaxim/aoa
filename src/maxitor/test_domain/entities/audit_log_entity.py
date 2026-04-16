# src/maxitor/test_domain/entities/audit_log_entity.py
"""Аудит — отдельный файл."""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel, entity
from maxitor.test_domain.domain import TestDomain
from maxitor.test_domain.entities.customer_order import TestOrderEntity


@entity(description="Test audit row", domain=TestDomain)
class TestAuditLogEntity(BaseEntity):
    id: str = Field(description="Audit id")
    action_performed: str = Field(description="Action label")
    actor_id: str = Field(description="Actor id")

    target_order: Annotated[
        AssociationOne[TestOrderEntity],
        NoInverse(),
    ] = Rel(description="Related order")  # type: ignore[assignment]
