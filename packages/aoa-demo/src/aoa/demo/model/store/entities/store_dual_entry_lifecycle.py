# packages/aoa-demo/src/aoa/demo/model/store/entities/store_dual_entry_lifecycle.py
"""Lifecycle with dual initial paths (demo)."""

from __future__ import annotations

from pydantic import Field

from aoa.action_machine.domain import (
    BaseStateEntity,
    Lifecycle,
    StateVocabulary,
)


class StoreDualEntryStateEntity(BaseStateEntity):
    """Status of the StoreDualEntry axis."""

    sort_order: int = Field(default=0, description="Presentation order")


class StoreDualEntryLifecycle(Lifecycle, StateVocabulary):
    """Lifecycle with **two** initial states (online vs walk-in), converging to one path."""

    ONLINE_DRAFT = StoreDualEntryStateEntity(code="online_draft", display_name="Online draft", sort_order=1)
    WALK_IN_QUOTE = StoreDualEntryStateEntity(code="walk_in_quote", display_name="Walk-in quote", sort_order=2)
    ACTIVE = StoreDualEntryStateEntity(code="active", display_name="Active", sort_order=3)
    FULFILLED = StoreDualEntryStateEntity(code="fulfilled", display_name="Fulfilled", sort_order=4)

    _template = (
        Lifecycle()
        .state(ONLINE_DRAFT)
        .to(ACTIVE)
        .initial()
        .state(WALK_IN_QUOTE)
        .to(ACTIVE)
        .initial()
        .state(ACTIVE)
        .to(FULFILLED)
        .intermediate()
        .state(FULFILLED)
        .final()
    )
