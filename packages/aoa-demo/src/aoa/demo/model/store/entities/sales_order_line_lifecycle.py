# packages/aoa-demo/src/aoa/demo/model/store/entities/sales_order_line_lifecycle.py
# pylint: disable=undefined-variable  # the class-name alias is the declaration surface
"""Sales order line lifecycle demo."""

from __future__ import annotations

from pydantic import Field

from aoa.action_machine.domain import (
    BaseStateEntity,
    Lifecycle,
    value,
)


class SalesOrderLineStateEntity(BaseStateEntity):
    """Status of the SalesOrderLine axis."""

    sort_order: int = Field(default=0, description="Presentation order")

    OPEN = value(code="open", display_name="Open", sort_order=1)
    RESERVED = value(code="reserved", display_name="Reserved", sort_order=2)
    FULFILLED = value(code="fulfilled", display_name="Fulfilled", sort_order=3)



class SalesOrderLineLifecycle(Lifecycle[SalesOrderLineStateEntity]):
    """Three states: open → reserved → fulfilled."""


    _template = (
        Lifecycle()
        .state(SalesOrderLineStateEntity.OPEN)
        .to(SalesOrderLineStateEntity.RESERVED)
        .initial()
        .state(SalesOrderLineStateEntity.RESERVED)
        .to(SalesOrderLineStateEntity.FULFILLED)
        .intermediate()
        .state(SalesOrderLineStateEntity.FULFILLED)
        .final()
    )
