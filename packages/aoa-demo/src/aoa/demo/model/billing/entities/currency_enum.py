# packages/aoa-demo/src/aoa/demo/model/billing/entities/currency_enum.py
"""Currency dictionaries the demo's monetary fields reference."""

from __future__ import annotations

from pydantic import Field

from aoa.action_machine.domain import BaseEnumEntity, value
from aoa.action_machine.intents.entity import entity
from aoa.demo.model.billing.domain import BillingDomain


@entity(description="Currency reference value", domain=BillingDomain)
class CurrencyEnumEntity(BaseEnumEntity):
    """Declare the currencies the demo uses, each one a value of this dictionary."""

    symbol: str = Field(description="Currency symbol")

    USD = value(code="usd", display_name="US dollar", symbol="$")
    EUR = value(code="eur", display_name="Euro", symbol="€")
    RUB = value(code="rub", display_name="Ruble", symbol="₽")
