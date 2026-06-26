# packages/aoa-demo/src/aoa/demo/model/store/entities/sales_order_line_lifecycle.py
"""Sales order line lifecycle demo."""

from __future__ import annotations

from aoa.action_machine.domain import Lifecycle


class SalesOrderLineLifecycle(Lifecycle):
    """Three states: open → reserved → fulfilled."""

    _template = (
        Lifecycle()
        .state("open", "Open")
        .to("reserved")
        .initial()
        .state("reserved", "Reserved")
        .to("fulfilled")
        .intermediate()
        .state("fulfilled", "Fulfilled")
        .final()
    )
