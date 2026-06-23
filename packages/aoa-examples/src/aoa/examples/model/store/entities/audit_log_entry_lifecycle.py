# packages/aoa-examples/src/aoa/examples/model/store/entities/audit_log_entry_lifecycle.py
"""Audit log entry lifecycle demo."""

from __future__ import annotations

from aoa.action_machine.domain import Lifecycle


class AuditLogEntryLifecycle(Lifecycle):
    """Three states: written → indexed → retained."""

    _template = (
        Lifecycle()
        .state("written", "Written")
        .to("indexed")
        .initial()
        .state("indexed", "Indexed")
        .to("retained")
        .intermediate()
        .state("retained", "Retained")
        .final()
    )
