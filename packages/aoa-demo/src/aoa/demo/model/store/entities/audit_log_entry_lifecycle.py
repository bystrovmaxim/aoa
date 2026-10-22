# packages/aoa-demo/src/aoa/demo/model/store/entities/audit_log_entry_lifecycle.py
# pylint: disable=undefined-variable  # the class-name alias is the declaration surface
"""Audit log entry lifecycle demo."""

from __future__ import annotations

from pydantic import Field

from aoa.action_machine.domain import (
    BaseStateEntity,
    Lifecycle,
)


class AuditLogEntryStateEntity(BaseStateEntity):
    """Status of the AuditLogEntry axis."""

    sort_order: int = Field(default=0, description="Presentation order")

    WRITTEN = AuditLogEntryStateEntity(code="written", display_name="Written", sort_order=1)  # noqa: F821
    INDEXED = AuditLogEntryStateEntity(code="indexed", display_name="Indexed", sort_order=2)  # noqa: F821
    RETAINED = AuditLogEntryStateEntity(code="retained", display_name="Retained", sort_order=3)  # noqa: F821



class AuditLogEntryLifecycle(Lifecycle[AuditLogEntryStateEntity]):
    """Three states: written → indexed → retained."""


    _template = (
        Lifecycle()
        .state(AuditLogEntryStateEntity.WRITTEN)
        .to(AuditLogEntryStateEntity.INDEXED)
        .initial()
        .state(AuditLogEntryStateEntity.INDEXED)
        .to(AuditLogEntryStateEntity.RETAINED)
        .intermediate()
        .state(AuditLogEntryStateEntity.RETAINED)
        .final()
    )
