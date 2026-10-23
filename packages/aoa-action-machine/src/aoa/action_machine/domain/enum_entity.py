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

        USD = value(code="usd", display_name="US dollar", symbol="$")
        EUR = value(code="eur", display_name="Euro", symbol="€")

``value`` returns a placeholder; after the class is created every name is a real
instance and the type carries the catalogue: ``members``, ``codes()``,
``by_code()`` and ``entity_type``. A class body cannot also bind the name
``value``; a model that needs such a field imports the factory under another
name.

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

    class body            conversion hook                consumers
    USD = value(...)  ──►  CurrencyEnumEntity(**kwargs) ──►  members, codes(),
    (ValueSpec placeholder)  full instance, validated       by_code(), entity_type
                                  │
                                  ├── interchange graph: properties.values
                                  └── a field typed by the dictionary: its reference object

═══════════════════════════════════════════════════════════════════════════════
USAGE
═══════════════════════════════════════════════════════════════════════════════

    @entity(description="Currency reference value", domain=ShopDomain)
    class CurrencyEnumEntity(BaseEnumEntity):
        symbol: str = Field(description="Currency symbol")

        USD = value(code="usd", display_name="US dollar", symbol="$")

    CurrencyEnumEntity.codes()          # ["usd"]
    CurrencyEnumEntity.by_code("usd")   # the declared USD value
"""

from __future__ import annotations

from abc import ABC
from collections.abc import Mapping
from typing import Any

from pydantic import (
    ConfigDict,
    Field,
    GetCoreSchemaHandler,
    SerializerFunctionWrapHandler,
    ValidationInfo,
    field_validator,
    model_serializer,
)
from pydantic_core import CoreSchema, core_schema

from aoa.action_machine.domain.declared_values import (
    ValueSpec,
    _DeclaredValues,
)
from aoa.action_machine.domain.entity import BaseEntity
from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model

_VALUE_CONSTRUCTION = object()


class BaseEnumEntity(_DeclaredValues, BaseEntity, ABC):
    """
    A shared reference value identified by its dictionary code.

    AI-CORE-BEGIN
        ROLE: A value of a closed reference dictionary — a currency, a country, an edition kind — declared in the dictionary type's own body and identified by its code.
        CONTRACT: The type declares its values in its class body; ``code`` is the identity inside the dictionary and ``display_name`` is the human label; ``members``, ``codes()``, ``by_code()`` and ``entity_type`` expose the catalogue; a field typed by the dictionary holds a declared value or its reference object; the reference form is the value's JSON export, so every leaf is JSON and a declared field serializer's text is what a consumer sees; the input JSON schema accepts a code-only reference and the output schema types each emitted property, the asymmetry being deliberate; the dictionary node carries its values in the graph, and a field typed by the dictionary is a reference: the graph carries one ``entity_reference`` edge to the dictionary beside the field row.
        INVARIANTS: Concrete dictionaries declare at least one value; codes are unique inside a dictionary; values are immutable and shared; a value's extra fields are limited to immutable types — str, int, float, bool, Decimal, date, datetime, time, UUID, an Enum, a Literal, Optional of those and tuples of them — because a list or a mapping would be reachable through `to_reference()`; the rule is checked twice, on the declared annotation and on the completed member after user validation, so a validator cannot publish a list, a value of another type, or an Enum whose own value is mutable; values are not inherited; no business Lifecycle; not a Specialization head, not a Generalization source, never a Composite target. A dated fact such as an exchange-rate quote is a separate business object, not another field of the dictionary.
    AI-CORE-END
    """

    model_config = ConfigDict(**BaseEntity.model_config, ignored_types=(ValueSpec,))

    __declared_values_inherit__ = False
    __declared_values_require_any__ = True
    __declared_values_immutable__ = True
    __declared_values_noun__ = "value"
    __declared_values_noun_plural__ = "values"
    __declared_values_empty_refusal__ = "a closed dictionary states its values."

    code: str = Field(description="Stable value code — identity inside the dictionary")
    display_name: str = Field(description="Human label for UI and diagrams")

    def __init__(self, **data: Any) -> None:  # pylint: disable=super-init-not-called
        """Build a value from its validated fields."""
        # Use BaseModel's validation path with a private, type-specific construction context.
        self.__pydantic_validator__.validate_python(data, self_instance=self, context=(_VALUE_CONSTRUCTION, type(self)))

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Hold every descendant to the kind's name suffix."""
        super().__init_subclass__(**kwargs)
        super()._require_kind_suffix("EnumEntity")

    @classmethod
    def __get_pydantic_core_schema__(  # pylint: disable=arguments-differ
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        """Accept a declared value or its reference object; refuse a bare code and a copy."""
        model_schema = handler(source_type)
        reference_keys = frozenset({"code", "display_name", "properties"})

        def normalize(value: Any, info: ValidationInfo) -> Any:
            """Resolve references while allowing the constructor to validate declared fields."""
            if info.context == (_VALUE_CONSTRUCTION, cls):
                return value
            if isinstance(value, cls):
                return cls._declared_member(value)
            if isinstance(value, str):
                raise ValueError(
                    f"{cls.__name__}: a bare code is not accepted; pass the declared value or its "
                    f"reference object {{'code', 'display_name', 'properties'}}."
                )
            if isinstance(value, Mapping):
                if not set(value) <= reference_keys:
                    raise ValueError(
                        f"{cls.__name__}: a reference object may only contain "
                        "'code', 'display_name' and 'properties'; put descriptive fields under 'properties'."
                    )
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

        return core_schema.with_info_before_validator_function(normalize, model_schema)

    @classmethod
    def __get_pydantic_json_schema__(  # pylint: disable=arguments-differ
        cls, schema: CoreSchema, handler: Any
    ) -> dict[str, Any]:
        """Publish the accepting shape in validation mode and the emitted shape in serialization mode."""
        if handler.mode == "serialization":
            return cls._emitted_reference_schema(schema, handler)
        return {
            "type": "object",
            "additionalProperties": False,
            "required": ["code"],
            "properties": {
                "code": {"type": "string", "minLength": 1},
                "display_name": {"type": "string", "minLength": 1},
                "properties": {"type": "object"},
            },
        }

    @classmethod
    def _emitted_reference_schema(cls, schema: CoreSchema, handler: Any) -> dict[str, Any]:
        """Describe the emitted reference: three members, each property by its serialized type."""
        model_schema = dict(schema)
        while model_schema.get("type") in {"function-before", "function-after", "function-wrap"}:
            model_schema = dict(model_schema["schema"])
        model_schema.pop("metadata", None)
        model_schema.pop("serialization", None)
        # The enclosing generator produces the property shapes, so the definitions a property
        # references stay registered and its `$ref` resolves in the finished document.
        emitted = handler(model_schema)
        properties = {
            name: {key: value for key, value in definition.items() if key not in {"title", "description"}}
            for name, definition in emitted.get("properties", {}).items()
            if name not in {"code", "display_name"}
        }
        # Requiredness follows the export, not the constructor: a property serialization always
        # writes is present even when its value is null, and an excluded one is not there at all.
        required = list(properties)
        return {
            "type": "object",
            "additionalProperties": False,
            "required": ["code", "display_name", "properties"],
            "properties": {
                "code": {"type": "string", "minLength": 1},
                "display_name": {"type": "string", "minLength": 1},
                "properties": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": properties,
                    "required": required,
                },
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

    @model_serializer(mode="wrap")
    def _serialize_as_reference(self, handler: SerializerFunctionWrapHandler) -> dict[str, Any]:
        """Serialize the value whole: its code, its label and its extra fields under ``properties``."""
        exported = handler(self)
        properties = {name: item for name, item in exported.items() if name not in {"code", "display_name"}}
        return {
            "code": exported["code"],
            "display_name": exported["display_name"],
            "properties": properties,
        }

    def to_reference(self) -> dict[str, Any]:
        """Return the value's reference form: the value's JSON export."""
        return self.model_dump(mode="json")

    @field_validator("code", "display_name")
    @classmethod
    def _reject_blank(cls, value: str) -> str:
        """Invariant: a code or a label is not empty and not whitespace-only."""
        if not value.strip():
            raise ValueError("An enum entity's 'code' and 'display_name' cannot be empty or whitespace-only.")
        return value


exclude_graph_model(BaseEnumEntity)
