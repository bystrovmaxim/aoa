# packages/aoa-demo/src/aoa/demo/model/store/entities/store_dual_entry_lifecycle.py
# pylint: disable=undefined-variable  # the class-name alias is the declaration surface
"""Lifecycle with dual initial paths (demo)."""

from __future__ import annotations

from pydantic import Field

from aoa.action_machine.domain import (
    BaseStateEntity,
    Lifecycle,
    value,
)


class StoreDualEntryStateEntity(BaseStateEntity):
    """Status of the StoreDualEntry axis."""

    sort_order: int = Field(default=0, description="Presentation order")

    ONLINE_DRAFT = value(code="online_draft", display_name="Online draft", sort_order=1)
    WALK_IN_QUOTE = value(code="walk_in_quote", display_name="Walk-in quote", sort_order=2)
    ACTIVE = value(code="active", display_name="Active", sort_order=3)
    FULFILLED = value(code="fulfilled", display_name="Fulfilled", sort_order=4)



class StoreDualEntryLifecycle(Lifecycle[StoreDualEntryStateEntity]):
    """Lifecycle with **two** initial states (online vs walk-in), converging to one path."""


    _template = (
        Lifecycle()
        .state(StoreDualEntryStateEntity.ONLINE_DRAFT)
        .to(StoreDualEntryStateEntity.ACTIVE)
        .initial()
        .state(StoreDualEntryStateEntity.WALK_IN_QUOTE)
        .to(StoreDualEntryStateEntity.ACTIVE)
        .initial()
        .state(StoreDualEntryStateEntity.ACTIVE)
        .to(StoreDualEntryStateEntity.FULFILLED)
        .intermediate()
        .state(StoreDualEntryStateEntity.FULFILLED)
        .final()
    )
