# packages/aoa-demo/src/aoa/demo/model/store/entities/audit_log_entry_lifecycle.py
"""Audit log entry lifecycle demo."""

from __future__ import annotations

from pydantic import Field

from aoa.action_machine.domain import (
    BaseStateEntity,
    Lifecycle,
    StateVocabulary,
)


class AuditLogEntryStateEntity(BaseStateEntity):
    """Status of the AuditLogEntry axis."""

    sort_order: int = Field(default=0, description="Presentation order")


class AuditLogEntryLifecycle(Lifecycle, StateVocabulary):
    """Three states: written → indexed → retained."""

    WRITTEN = AuditLogEntryStateEntity(code="written", display_name="Written", sort_order=1)
    INDEXED = AuditLogEntryStateEntity(code="indexed", display_name="Indexed", sort_order=2)
    RETAINED = AuditLogEntryStateEntity(code="retained", display_name="Retained", sort_order=3)

    _template = (
        Lifecycle()
        .state(WRITTEN)
        .to(INDEXED)
        .initial()
        .state(INDEXED)
        .to(RETAINED)
        .intermediate()
        .state(RETAINED)
        .final()
    )
