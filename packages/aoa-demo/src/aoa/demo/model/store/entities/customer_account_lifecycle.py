# packages/aoa-demo/src/aoa/demo/model/store/entities/customer_account_lifecycle.py
"""Customer account lifecycle demo."""

from __future__ import annotations

from pydantic import Field

from aoa.action_machine.domain import (
    BaseStateEntity,
    Lifecycle,
    StateVocabulary,
)


class CustomerAccountStateEntity(BaseStateEntity):
    """Status of the CustomerAccount axis."""

    sort_order: int = Field(default=0, description="Presentation order")


class CustomerAccountLifecycle(Lifecycle, StateVocabulary):
    """Three states: provisioned → active → closed."""

    PROVISIONED = CustomerAccountStateEntity(code="provisioned", display_name="Provisioned", sort_order=1)
    ACTIVE = CustomerAccountStateEntity(code="active", display_name="Active", sort_order=2)
    CLOSED = CustomerAccountStateEntity(code="closed", display_name="Closed", sort_order=3)

    _template = (
        Lifecycle()
        .state(PROVISIONED)
        .to(ACTIVE)
        .initial()
        .state(ACTIVE)
        .to(CLOSED)
        .intermediate()
        .state(CLOSED)
        .final()
    )
