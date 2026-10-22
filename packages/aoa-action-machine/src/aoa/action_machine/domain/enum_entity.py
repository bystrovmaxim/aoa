# packages/aoa-action-machine/src/aoa/action_machine/domain/enum_entity.py
"""
BaseEnumEntity — the base class of the enum kind: a closed reference dictionary.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

One of the six base classes a real entity inherits from, and the dictionary of
its kind: a value other objects refer to, declared in the dictionary type's own
body, the way a state type declares its statuses::

    @entity(description="Currency reference value", domain=ShopDomain)
    class CurrencyEnumEntity(BaseEnumEntity):
        symbol: str = Field(description="Currency symbol")

        USD = CurrencyEnumEntity(code="usd", display_name="US dollar", symbol="$")
        EUR = CurrencyEnumEntity(code="eur", display_name="Euro", symbol="€")

Inside the body the type's name resolves to the internal declaration factory;
after the class is created every name is a real instance and the type carries the
catalogue: ``members``, ``codes()``, ``by_code()`` and ``entity_type``.

The set is closed: a dictionary declares every value it has, and nothing else is
a value. A dictionary maintained in data is a different kind.

═══════════════════════════════════════════════════════════════════════════════
SCOPE (IN / OUT)
═══════════════════════════════════════════════════════════════════════════════

**In scope**
    The kind word, the name rule of the kind, ``code`` and ``display_name`` with
    their non-blank rules, the declaration of the values, the catalogue, the
    duplicate refusal, and the reference form the graph and the wire carry.

**Out of scope**
    Storage and transport schemas — separate work. A dictionary maintained in
    data — a different kind. The hierarchy rules — ``BaseEntity`` owns them.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    class body                      conversion hook              consumers
    USD = CurrencyEnumEntity(...) ──►  CurrencyEnumEntity(...) ──►  members, codes(),
    (ValueSpec placeholder)            full instance, validated     by_code(), entity_type
                                  │
                                  ├── interchange graph: properties.values
                                  └── a field typed by the dictionary: its reference object

═══════════════════════════════════════════════════════════════════════════════
USAGE
═══════════════════════════════════════════════════════════════════════════════

    @entity(description="Currency reference value", domain=ShopDomain)
    class CurrencyEnumEntity(BaseEnumEntity):
        symbol: str = Field(description="Currency symbol")

        USD = CurrencyEnumEntity(code="usd", display_name="US dollar", symbol="$")

    CurrencyEnumEntity.codes()          # ["usd"]
    CurrencyEnumEntity.by_code("usd")   # the declared USD value
"""

from __future__ import annotations

from abc import ABC
from collections.abc import Mapping
from typing import Any

from pydantic import ConfigDict, Field, GetCoreSchemaHandler, field_validator
from pydantic_core import CoreSchema, core_schema

from aoa.action_machine.domain.declared_values import (
    DeclaredValuesMeta,
    ValueSpec,
    _DeclaredValues,
)
from aoa.action_machine.domain.entity import BaseEntity
from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model


class BaseEnumEntity(_DeclaredValues, BaseEntity, ABC, metaclass=DeclaredValuesMeta):
    """
    A shared reference value identified by its dictionary code.

    AI-CORE-BEGIN
        ROLE: A value of a closed reference dictionary — a currency, a country, an edition kind — declared in the dictionary type's own body and identified by its code.
        CONTRACT: The type declares its values in its class body; ``code`` is the identity inside the dictionary and ``display_name`` is the human label; ``members``, ``codes()``, ``by_code()`` and ``entity_type`` expose the catalogue; a field typed by the dictionary holds a declared value or its reference object; the dictionary node carries its values in the graph.
        INVARIANTS: Concrete dictionaries declare at least one value; codes are unique inside a dictionary; values are immutable and shared; values are not inherited; no business Lifecycle; not a Specialization head, not a Generalization source, never a Composite target. A dated fact such as an exchange-rate quote is a separate business object, not another field of the dictionary.
    AI-CORE-END
    """

    model_config = ConfigDict(**BaseEntity.model_config, ignored_types=(ValueSpec,))

    __declared_values_inherit__ = False
    __declared_values_require_any__ = True
    __declared_values_noun__ = "value"
    __declared_values_noun_plural__ = "values"
    __declared_values_empty_refusal__ = "a closed dictionary states its values."

    code: str = Field(description="Stable value code — identity inside the dictionary")
    display_name: str = Field(description="Human label for UI and diagrams")

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Hold every descendant to the kind's name suffix."""
        super().__init_subclass__(**kwargs)
        super()._require_kind_suffix("EnumEntity")

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: GetCoreSchemaHandler) -> CoreSchema:
        """Accept a declared value or its reference object; refuse a bare code and a copy."""
        model_schema = handler(source_type)
        reference_keys = frozenset({"code", "display_name", "properties"})

        def normalize(value: Any) -> Any:
            if isinstance(value, cls):
                return cls._declared_member(value)
            if isinstance(value, str):
                raise ValueError(
                    f"{cls.__name__}: a bare code is not accepted; pass the declared value or its "
                    f"reference object {{'code', 'display_name', 'properties'}}."
                )
            if isinstance(value, Mapping) and set(value) <= reference_keys:
                if not cls.members:
                    # the class is being created: its own values are constructed, not referenced
                    return value
                code = value.get("code")
                if not isinstance(code, str) or not code.strip():
                    raise ValueError(f"{cls.__name__}: a reference object needs a non-empty 'code'.")
                try:
                    return cls.by_code(code)
                except KeyError:
                    raise ValueError(
                        f"'{code}' is not a declared value of {cls.__name__}. Declared: {cls.codes()}."
                    ) from None
            return value

        return core_schema.no_info_before_validator_function(
            normalize,
            model_schema,
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda declared: declared.to_reference(),
                return_schema=core_schema.any_schema(),
            ),
        )

    @classmethod
    def __get_pydantic_json_schema__(cls, schema: CoreSchema, handler: Any) -> dict[str, Any]:
        """Publish the reference object as this type's JSON shape."""
        _ = (schema, handler)
        return {
            "type": "object",
            "additionalProperties": False,
            "required": ["code", "display_name", "properties"],
            "properties": {
                "code": {"type": "string", "minLength": 1},
                "display_name": {"type": "string", "minLength": 1},
                "properties": {"type": "object"},
            },
        }

    @classmethod
    def _declared_member(cls, value: Any) -> Any:
        """Return the declared value ``value`` is, or refuse a copy."""
        for member in cls.members:
            if value is member:
                return member
        raise ValueError(
            f"{cls.__name__}: a copy of a declared value is not a value; "
            f"use the declared attribute (for example {cls.__name__}.{cls._attribute_of(value)})."
        )

    @classmethod
    def _attribute_of(cls, member: Any) -> str:
        """Return the class attribute a declared value is bound to, or a placeholder."""
        for name, value in cls.__dict__.items():
            if value is member:
                return str(name)
        return "<value>"

    def to_reference(self) -> dict[str, Any]:
        """Return the value's reference form: its code, its label and its extra fields."""
        extra = {
            name: getattr(self, name)
            for name in type(self).model_fields
            if name not in {"code", "display_name"}
        }
        return {"code": self.code, "display_name": self.display_name, "properties": extra}

    @field_validator("code", "display_name")
    @classmethod
    def _reject_blank(cls, value: str) -> str:
        """Invariant: a code or a label is not empty and not whitespace-only."""
        if not value.strip():
            raise ValueError("An enum entity's 'code' and 'display_name' cannot be empty or whitespace-only.")
        return value


exclude_graph_model(BaseEnumEntity)
