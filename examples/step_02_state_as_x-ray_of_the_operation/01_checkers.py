"""
# 01_checkers.py — All result_* checkers and their parameters

Every @regular_aspect publishes a typed contract via @result_* decorators.
This file shows all six checker types in one pipeline step:

  result_string   — string, optional min_length / max_length / not_empty
  result_int      — integer, optional min_value / max_value
  result_float    — float, optional min_value / max_value
  result_bool     — boolean flag
  result_date     — datetime or formatted date-string, optional date_format / min_date / max_date
  result_instance — class instance, optional no_none / value_check lambda

Common parameters shared by all checkers:
  required=True  (default) — field must be present and non-None after the aspect
  required=False           — field may be absent from the returned dict (skipped if missing)
  opaque=True              — exclude from OTel state x-ray (see 07_opaque.py)

The example runs twice: once with a coupon code, once without.
The optional field result_string("coupon_code", required=False) demonstrates
that the checker is silently skipped when the key is not in the returned dict.

Run:
    uv run python examples/step_02_state_as_x-ray_of_the_operation/01_checkers.py
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime

from pydantic import Field

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.context import Context
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import regular_aspect, summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.checkers import (
    result_bool,
    result_date,
    result_float,
    result_instance,
    result_int,
    result_string,
)
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.logging import Channel, ConsoleLogger
from aoa.action_machine.logging.log_coordinator import LogCoordinator
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine


# ---------------------------------------------------------------------------
# Domain
# ---------------------------------------------------------------------------

class OrderDomain(BaseDomain):
    name = "order"
    description = "Order intake and validation domain"


# ---------------------------------------------------------------------------
# Supporting types
# ---------------------------------------------------------------------------

@dataclass
class CustomerProfile:
    name: str
    is_active: bool


# ---------------------------------------------------------------------------
# Params and Result
# ---------------------------------------------------------------------------

class OrderParams(BaseParams):
    order_id: str = Field(description="Raw order identifier from the client")
    quantity: int = Field(description="Number of units")
    unit_price: float = Field(description="Price per unit in USD")
    is_urgent: bool = Field(description="Whether express processing is requested")
    delivery_date: str = Field(description="Requested delivery date (YYYY-MM-DD)")
    customer_name: str = Field(description="Full name of the customer")
    coupon_code: str | None = Field(default=None, description="Optional discount coupon")


class OrderResult(BaseResult):
    order_id: str = Field(description="Normalised order ID (uppercased)")
    total: float = Field(description="Computed order total")
    is_urgent: bool = Field(description="Express processing flag")
    has_coupon: bool = Field(description="Whether a coupon was applied")


# ---------------------------------------------------------------------------
# Action
# ---------------------------------------------------------------------------

@meta(description="Validate and normalise an incoming order", domain=OrderDomain)
@check_roles(GuestRole)
class ValidateOrderAction(BaseAction[OrderParams, OrderResult]):

    # -----------------------------------------------------------------------
    # Single validation step — every checker type in one place.
    #
    # result_string("order_id", min_length=5, max_length=20)
    #   Value must be a string between 5 and 20 characters.
    #
    # result_int("quantity", min_value=1, max_value=999)
    #   Integer inside [1, 999]. Both bounds are inclusive.
    #
    # result_float("unit_price", min_value=0.01)
    #   Float ≥ 0.01. No upper bound.
    #
    # result_bool("is_urgent")
    #   Must be a boolean (True or False). No extra params.
    #
    # result_date("delivery_date", date_format="%Y-%m-%d", min_date=...)
    #   String parsed with strptime, must be after 2024-01-01.
    #   Accepts a datetime object directly too (format not required then).
    #
    # result_instance("customer", CustomerProfile, no_none=True, value_check=...)
    #   Must be a CustomerProfile instance. no_none=True rejects explicit None
    #   even when the key is present. value_check receives the object and must
    #   return True — here we require an active account.
    #
    # result_string("coupon_code", required=False)
    #   May be absent from the returned dict. If present, must be a string.
    #   Run the example twice (with and without coupon) to see the difference.
    # -----------------------------------------------------------------------

    @regular_aspect("Validate and normalise all order fields")
    @result_string("order_id", required=True, min_length=5, max_length=20)
    @result_int("quantity", required=True, min_value=1, max_value=999)
    @result_float("unit_price", required=True, min_value=0.01)
    @result_bool("is_urgent", required=True)
    @result_date("delivery_date", required=True, date_format="%Y-%m-%d",
                 min_date=datetime(2024, 1, 1))
    @result_instance("customer", CustomerProfile, required=True, no_none=True,
                     value_check=lambda c: c.is_active)
    @result_string("coupon_code", required=False)
    async def validate_aspect(self, params, state, box, connections):
        result: dict = {
            "order_id": params.order_id.strip().upper(),
            "quantity": params.quantity,
            "unit_price": params.unit_price,
            "is_urgent": params.is_urgent,
            "delivery_date": params.delivery_date,
            "customer": CustomerProfile(name=params.customer_name, is_active=True),
        }
        if params.coupon_code:
            result["coupon_code"] = params.coupon_code.strip().upper()
        # coupon_code absent from dict when not provided → required=False → no error
        return result

    @summary_aspect("Assemble validated order result")
    async def assemble_summary(self, params, state, box, connections):
        total = round(state["quantity"] * state["unit_price"], 2)
        has_coupon = "coupon_code" in state
        await box.info(
            Channel.business,
            "order_id={%var.order_id}  total={%var.total}  urgent={%var.urgent}  coupon={%var.coupon}",
            order_id=state["order_id"],
            total=total,
            urgent=state["is_urgent"],
            coupon=has_coupon,
        )
        return OrderResult(
            order_id=state["order_id"],
            total=total,
            is_urgent=state["is_urgent"],
            has_coupon=has_coupon,
        )


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

async def main() -> None:
    machine = ActionProductMachine(
        log_coordinator=LogCoordinator(loggers=[ConsoleLogger()]),
    )

    print("Run 1: order with coupon code")
    await machine.run(
        Context(),
        ValidateOrderAction(),
        OrderParams(
            order_id="  ord-2024-001  ",
            quantity=3,
            unit_price=49.99,
            is_urgent=True,
            delivery_date="2025-12-01",
            customer_name="Alice",
            coupon_code="  summer20  ",
        ),
    )

    print("\nRun 2: order without coupon (required=False → no error)")
    await machine.run(
        Context(),
        ValidateOrderAction(),
        OrderParams(
            order_id="ord-2024-002",
            quantity=1,
            unit_price=9.99,
            is_urgent=False,
            delivery_date="2025-06-15",
            customer_name="Bob",
            coupon_code=None,
        ),
    )


asyncio.run(main())
