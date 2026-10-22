# packages/aoa-action-machine/src/aoa/action_machine/domain/enum_entity.py
"""
BaseEnumEntity — the base class of the enum kind: a shared reference value.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

One of the six base classes a real entity inherits from. It states what an
instance represents in the domain, declares its kind as one word, and holds its
descendants to the kind's name suffix. The other five are declared beside it in this
package, one file each, and the entity base holds the hierarchy rules.

═══════════════════════════════════════════════════════════════════════════════
USAGE
═══════════════════════════════════════════════════════════════════════════════

    @entity(description="Shared currency value", domain=ShopDomain)
    class CurrencyEnumEntity(BaseEnumEntity):
        code: str = Field(description="Currency code")
        symbol: str = Field(description="Currency symbol")
"""

from __future__ import annotations

from abc import ABC
from typing import Any

from aoa.action_machine.domain.entity import BaseEntity
from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model


@exclude_graph_model
class BaseEnumEntity(BaseEntity, ABC):
    """
    A shared reference value identified by its dictionary code.

    AI-CORE-BEGIN
        ROLE: A value from a reference dictionary — a currency, a country, an edition kind — identified by its code, with additional fields describing the value.
        CONTRACT: Many objects may refer to it without owning it; the fields describe the reference value itself.
        INVARIANTS: No business Lifecycle; not a Specialization head, not a Generalization source, never a Composite target. A dated fact such as an exchange-rate quote is a separate business object, not another field of the dictionary.
    AI-CORE-END
    """

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Hold every descendant to the kind's name suffix."""
        super().__init_subclass__(**kwargs)
        super()._require_kind_suffix("EnumEntity")
