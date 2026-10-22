# packages/aoa-demo/src/aoa/demo/model/dictionaries/entities/currency_enum.py
"""Currency dictionaries the demo's monetary fields reference."""

# pylint: disable=undefined-variable  # the class-name alias is the declaration surface

from __future__ import annotations

from pydantic import Field

from aoa.action_machine.domain import BaseEnumEntity
from aoa.action_machine.intents.entity import entity
from aoa.demo.model.dictionaries.domain import DictionariesDomain


@entity(description="Currency reference value", domain=DictionariesDomain)
class CurrencyEnumEntity(BaseEnumEntity):
    """Declare the currencies the demo uses, each one a value of this dictionary."""

    symbol: str = Field(description="Currency symbol")

    USD = CurrencyEnumEntity(code="usd", display_name="US dollar", symbol="$")  # noqa: F821
    EUR = CurrencyEnumEntity(code="eur", display_name="Euro", symbol="€")  # noqa: F821
    RUB = CurrencyEnumEntity(code="rub", display_name="Ruble", symbol="₽")  # noqa: F821
