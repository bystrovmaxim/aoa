# packages/aoa-demo/src/aoa/demo/model/billing/entities/payment_lifecycle.py
"""Lifecycle graph for payment-event entity (parallel to ``SalesOrderLifecycle`` in store)."""

from pydantic import Field

from aoa.action_machine.domain import (
    BaseStateEntity,
    Lifecycle,
    StateVocabulary,
)


class PaymentEventStateEntity(BaseStateEntity):
    """Status of the PaymentEvent axis."""

    sort_order: int = Field(default=0, description="Presentation order")


class PaymentEventLifecycle(Lifecycle, StateVocabulary):
    """Three states: recorded → settled → archived."""

    RECORDED = PaymentEventStateEntity(code="recorded", display_name="Recorded", sort_order=1)
    SETTLED = PaymentEventStateEntity(code="settled", display_name="Settled", sort_order=2)
    ARCHIVED = PaymentEventStateEntity(code="archived", display_name="Archived", sort_order=3)

    _template = (
        Lifecycle()
        .state(RECORDED)
        .to(SETTLED)
        .initial()
        .state(SETTLED)
        .to(ARCHIVED)
        .intermediate()
        .state(ARCHIVED)
        .final()
    )
