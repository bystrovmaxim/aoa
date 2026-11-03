# packages/aoa-demo/src/aoa/demo/model/store/entities/audit_log_entry_lifecycle.py
"""Audit log entry lifecycle demo."""

from __future__ import annotations

from pydantic import Field

from aoa.action_machine.domain import (
    BaseStateEntity,
    Lifecycle,
    value,
)


class AuditLogEntryStateEntity(BaseStateEntity):
    """Status of the AuditLogEntry axis."""

    sort_order: int = Field(default=0, description="Presentation order")

    WRITTEN = value(code="written", display_name="Written", sort_order=1)
    RETAINED = value(code="retained", display_name="Retained", sort_order=2)



class AuditLogEntryLifecycle(Lifecycle[AuditLogEntryStateEntity]):
    """Two states: written → retained."""


    _template = (
        Lifecycle()
        .state(AuditLogEntryStateEntity.WRITTEN)
        .to(AuditLogEntryStateEntity.RETAINED)
        .initial()
        .state(AuditLogEntryStateEntity.RETAINED)
        .final()
    )
