# packages/aoa-demo/src/aoa/demo/model/store/entities/subscription_lifecycle.py
"""Subscription lifecycle demo."""

from __future__ import annotations

from pydantic import Field

from aoa.action_machine.domain import (
    BaseStateEntity,
    Lifecycle,
    value,
)


class SubscriptionStateEntity(BaseStateEntity):
    """Status of the Subscription axis."""

    sort_order: int = Field(default=0, description="Presentation order")

    TRIAL = value(code="trial", display_name="Trial", sort_order=1)
    ACTIVE = value(code="active", display_name="Active", sort_order=2)
    CANCELLED = value(code="cancelled", display_name="Cancelled", sort_order=3)


class SubscriptionLifecycle(Lifecycle[SubscriptionStateEntity]):
    """Three states: trial → active → cancelled; a trial may also be cancelled."""

    _template = (
        Lifecycle()
        .state(SubscriptionStateEntity.TRIAL)
        .to(SubscriptionStateEntity.ACTIVE, SubscriptionStateEntity.CANCELLED)
        .initial()
        .state(SubscriptionStateEntity.ACTIVE)
        .to(SubscriptionStateEntity.CANCELLED)
        .intermediate()
        .state(SubscriptionStateEntity.CANCELLED)
        .final()
    )
