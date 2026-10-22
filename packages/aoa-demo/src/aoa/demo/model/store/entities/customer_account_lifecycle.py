# packages/aoa-demo/src/aoa/demo/model/store/entities/customer_account_lifecycle.py
# pylint: disable=undefined-variable  # the class-name alias is the declaration surface
"""Customer account lifecycle demo."""

from __future__ import annotations

from pydantic import Field

from aoa.action_machine.domain import (
    BaseStateEntity,
    Lifecycle,
)


class CustomerAccountStateEntity(BaseStateEntity):
    """Status of the CustomerAccount axis."""

    sort_order: int = Field(default=0, description="Presentation order")

    PROVISIONED = CustomerAccountStateEntity(code="provisioned", display_name="Provisioned", sort_order=1)  # noqa: F821
    ACTIVE = CustomerAccountStateEntity(code="active", display_name="Active", sort_order=2)  # noqa: F821
    CLOSED = CustomerAccountStateEntity(code="closed", display_name="Closed", sort_order=3)  # noqa: F821



class CustomerAccountLifecycle(Lifecycle[CustomerAccountStateEntity]):
    """Three states: provisioned → active → closed."""


    _template = (
        Lifecycle()
        .state(CustomerAccountStateEntity.PROVISIONED)
        .to(CustomerAccountStateEntity.ACTIVE)
        .initial()
        .state(CustomerAccountStateEntity.ACTIVE)
        .to(CustomerAccountStateEntity.CLOSED)
        .intermediate()
        .state(CustomerAccountStateEntity.CLOSED)
        .final()
    )
