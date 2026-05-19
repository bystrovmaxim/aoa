# packages/aoa-examples/src/aoa/examples/model/store/entities/store_dual_entry_lifecycle.py
"""Lifecycle with dual initial paths (demo)."""

from __future__ import annotations

from aoa.action_machine.domain import Lifecycle


class StoreDualEntryLifecycle(Lifecycle):
    """Lifecycle with **two** initial states (online vs walk-in), converging to one path."""

    _template = (
        Lifecycle()
        .state("online_draft", "Online draft").to("active").initial()
        .state("walk_in_quote", "Walk-in quote").to("active").initial()
        .state("active", "Active").to("fulfilled").intermediate()
        .state("fulfilled", "Fulfilled").final()
    )
