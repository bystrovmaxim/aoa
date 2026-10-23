# packages/aoa-demo/src/aoa/demo/model/billing/entities/payment_lifecycle.py
# pylint: disable=undefined-variable  # the class-name alias is the declaration surface
"""Lifecycle graph for payment-event entity (parallel to ``SalesOrderLifecycle`` in store)."""

from pydantic import Field

from aoa.action_machine.domain import (
    BaseStateEntity,
    Lifecycle,
    value,
)


class PaymentEventStateEntity(BaseStateEntity):
    """Status of the PaymentEvent axis."""

    sort_order: int = Field(default=0, description="Presentation order")

    RECORDED = value(code="recorded", display_name="Recorded", sort_order=1)
    SETTLED = value(code="settled", display_name="Settled", sort_order=2)
    ARCHIVED = value(code="archived", display_name="Archived", sort_order=3)



class PaymentEventLifecycle(Lifecycle[PaymentEventStateEntity]):
    """Three states: recorded → settled → archived."""


    _template = (
        Lifecycle()
        .state(PaymentEventStateEntity.RECORDED)
        .to(PaymentEventStateEntity.SETTLED)
        .initial()
        .state(PaymentEventStateEntity.SETTLED)
        .to(PaymentEventStateEntity.ARCHIVED)
        .intermediate()
        .state(PaymentEventStateEntity.ARCHIVED)
        .final()
    )
