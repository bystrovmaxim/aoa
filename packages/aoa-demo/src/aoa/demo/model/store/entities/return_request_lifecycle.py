# packages/aoa-demo/src/aoa/demo/model/store/entities/return_request_lifecycle.py
"""Return request lifecycle demo."""

from __future__ import annotations

from pydantic import Field

from aoa.action_machine.domain import (
    BaseStateEntity,
    Lifecycle,
    value,
)


class ReturnRequestStateEntity(BaseStateEntity):
    """Status of the ReturnRequest axis."""

    sort_order: int = Field(default=0, description="Presentation order")

    REQUESTED = value(code="requested", display_name="Requested", sort_order=1)
    APPROVED = value(code="approved", display_name="Approved", sort_order=2)
    REJECTED = value(code="rejected", display_name="Rejected", sort_order=3)
    REFUNDED = value(code="refunded", display_name="Refunded", sort_order=4)


class ReturnRequestLifecycle(Lifecycle[ReturnRequestStateEntity]):
    """A return is requested, then approved and refunded, or rejected."""

    _template = (
        Lifecycle()
        .state(ReturnRequestStateEntity.REQUESTED)
        .to(ReturnRequestStateEntity.APPROVED, ReturnRequestStateEntity.REJECTED)
        .initial()
        .state(ReturnRequestStateEntity.APPROVED)
        .to(ReturnRequestStateEntity.REFUNDED)
        .intermediate()
        .state(ReturnRequestStateEntity.REJECTED)
        .final()
        .state(ReturnRequestStateEntity.REFUNDED)
        .final()
    )
