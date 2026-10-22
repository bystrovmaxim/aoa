# packages/aoa-demo/src/aoa/demo/model/store/entities/sales_order_line_lifecycle.py
# pylint: disable=undefined-variable  # the class-name alias is the declaration surface
"""Sales order line lifecycle demo."""

from __future__ import annotations

from pydantic import Field

from aoa.action_machine.domain import (
    BaseStateEntity,
    Lifecycle,
)


class SalesOrderLineStateEntity(BaseStateEntity):
    """Status of the SalesOrderLine axis."""

    sort_order: int = Field(default=0, description="Presentation order")

    OPEN = SalesOrderLineStateEntity(code="open", display_name="Open", sort_order=1)  # noqa: F821
    RESERVED = SalesOrderLineStateEntity(code="reserved", display_name="Reserved", sort_order=2)  # noqa: F821
    FULFILLED = SalesOrderLineStateEntity(code="fulfilled", display_name="Fulfilled", sort_order=3)  # noqa: F821



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
