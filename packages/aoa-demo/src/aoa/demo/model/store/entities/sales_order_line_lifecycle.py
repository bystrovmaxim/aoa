# packages/aoa-demo/src/aoa/demo/model/store/entities/sales_order_line_lifecycle.py
"""Sales order line lifecycle demo."""

from __future__ import annotations

from pydantic import Field

from aoa.action_machine.domain import (
    BaseStateEntity,
    Lifecycle,
    StateVocabulary,
)


class SalesOrderLineStateEntity(BaseStateEntity):
    """Status of the SalesOrderLine axis."""

    sort_order: int = Field(default=0, description="Presentation order")


class SalesOrderLineLifecycle(Lifecycle, StateVocabulary):
    """Three states: open → reserved → fulfilled."""

    OPEN = SalesOrderLineStateEntity(code="open", display_name="Open", sort_order=1)
    RESERVED = SalesOrderLineStateEntity(code="reserved", display_name="Reserved", sort_order=2)
    FULFILLED = SalesOrderLineStateEntity(code="fulfilled", display_name="Fulfilled", sort_order=3)

    _template = (
        Lifecycle()
        .state(OPEN)
        .to(RESERVED)
        .initial()
        .state(RESERVED)
        .to(FULFILLED)
        .intermediate()
        .state(FULFILLED)
        .final()
    )
