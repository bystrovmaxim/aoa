# packages/aoa-action-machine/src/aoa/action_machine/domain/state_entity.py
"""
BaseStateEntity — the marker of the state kind: a status type that owns its statuses.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

One of the six base classes a real entity inherits from, and the only one that
carries fields: a status is one state of one lifecycle axis, with a stable
``code`` the machine uses as the state key, a ``display_name`` the diagrams
show, and whatever domain fields the status needs.

The type also declares its own statuses in its own body::

    class OrderStateEntity(BaseStateEntity):
        DRAFT = OrderStateEntity(code="draft", display_name="Draft")

Inside the body the type's name resolves to the internal declaration factory;
after the class is created every name is a real instance and the type carries
the catalogue: ``members``, ``codes()``, ``by_code()`` and ``entity_type``.

═══════════════════════════════════════════════════════════════════════════════
SCOPE (IN / OUT)
═══════════════════════════════════════════════════════════════════════════════

**In scope**
    The kind word, the name rule of the kind, the two required fields and their
    non-blank validation, the declaration placeholders and their conversion into
    instances, the catalogue, and the automatic exclusion of every status type
    from the interchange graph.

**Out of scope**
    Classification and transitions — ``Lifecycle``. The axis checks — the
    generic ``Lifecycle``. Persistence and transport — separate work.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    class body                     conversion hook                 consumers
    DRAFT = OrderStateEntity(...)  ──►  OrderStateEntity(**kwargs)  ──►  members,
    (StateSpec placeholder)            full instance, fields validated    codes(), by_code(),
                                                                          entity_type
                                  │
                                  ├── lifecycle template: key = code, label = display_name
                                  └── interchange graph: label + properties.attributes

═══════════════════════════════════════════════════════════════════════════════
USAGE
═══════════════════════════════════════════════════════════════════════════════

    class OrderStateEntity(BaseStateEntity):
        sort_order: int = Field(default=0, description="Presentation order")

        DRAFT = OrderStateEntity(code="draft", display_name="Draft", sort_order=99)
        PAID = OrderStateEntity(code="paid", display_name="Paid", sort_order=1)
"""

from __future__ import annotations

from abc import ABC
from typing import Any, ClassVar

from pydantic import ConfigDict, Field, field_validator
from pydantic._internal._model_construction import ModelMetaclass

from aoa.action_machine.domain.entity import BaseEntity
from aoa.action_machine.domain.state_spec import StateSpec, state
from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model


class _StateNamespace(dict[str, Any]):
    """The class namespace that answers the state type's own name with the factory."""

    def __init__(self, name: str) -> None:
        """Remember the class name this namespace belongs to."""
        super().__init__()
        self._name = name

    def __getitem__(self, key: str) -> Any:
        """Return the stored value, or the declaration factory for the class's own name."""
        try:
            return super().__getitem__(key)
        except KeyError:
            if key == self._name:
                return state
            raise


class StateEntityMeta(ModelMetaclass):
    """Metaclass of the state kind: the class's own name is the declaration factory."""

    @classmethod
    def __prepare__(mcs, *args: Any, **kwargs: Any) -> dict[str, Any]:  # noqa: N804
        """Give the class body the alias before the class itself exists."""
        _ = mcs  # the metaclass is bound by the class machinery; the name keeps the pylint contract
        name = args[0] if args else kwargs.get("name", "")
        return _StateNamespace(str(name))


class BaseStateEntity(BaseEntity, ABC, metaclass=StateEntityMeta):
    """
    AI-CORE-BEGIN
        ROLE: Marker of the state kind — a status type that declares its own statuses and carries their catalogue.
        CONTRACT: ``code`` is the identity of the status inside ``Lifecycle``; ``display_name`` is the human label carried into the interchange graph; after class creation every declared status is an instance and ``members``, ``codes()``, ``by_code()`` and ``entity_type`` expose the catalogue; every descendant is kept out of the model graph.
        INVARIANTS: Immutable; ``code`` and ``display_name`` are non-empty after strip; statuses share the declaring type; codes are unique; a subclass with no statuses inherits the parent's catalogue; a placeholder is never a model field.
    AI-CORE-END
    """

    model_config = ConfigDict(**BaseEntity.model_config, ignored_types=(StateSpec,))

    code: str = Field(description="Stable state code — identity inside the lifecycle")
    display_name: str = Field(description="Human label for UI and diagrams")

    members: ClassVar[tuple[BaseStateEntity, ...]] = ()
    _by_code: ClassVar[dict[str, BaseStateEntity]] = {}
    entity_type: ClassVar[type[BaseStateEntity] | None] = None

    def __init__(self, **data: Any) -> None:  # pylint: disable=useless-parent-delegation
        """Build a status from its validated fields."""
        super().__init__(**data)

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Hold every status type to the kind's name suffix and out of the interchange graph."""
        super().__init_subclass__(**kwargs)
        super()._require_kind_suffix("StateEntity")
        exclude_graph_model(cls)

    @classmethod
    def __pydantic_init_subclass__(cls, **kwargs: Any) -> None:
        """Turn this state type's placeholders into status instances and fill its catalogue."""
        super().__pydantic_init_subclass__(**kwargs)
        cls.entity_type = cls
        specs = {name: value for name, value in cls.__dict__.items() if isinstance(value, StateSpec)}
        if not specs:
            return
        for name, spec in specs.items():
            setattr(cls, name, cls(**spec.kwargs))
        members = tuple(getattr(cls, name) for name in specs)
        codes = [member.code for member in members]
        if len(codes) != len(set(codes)):
            duplicates = sorted({code for code in codes if codes.count(code) > 1})
            raise ValueError(f"{cls.__name__}: duplicate status code(s) in {duplicates}.")
        cls.members = members
        cls._by_code = {member.code: member for member in members}

    @classmethod
    def codes(cls) -> list[str]:
        """Return the declared status codes in declaration order."""
        return [member.code for member in cls.members]

    @classmethod
    def by_code(cls, code: str) -> BaseStateEntity:
        """Return the status declared under ``code``; raise ``KeyError`` otherwise."""
        return cls._by_code[code]

    @field_validator("code", "display_name")
    @classmethod
    def _reject_blank(cls, value: str) -> str:
        """Invariant: a code or a label is not empty and not whitespace-only."""
        if not value.strip():
            raise ValueError("A state entity's 'code' and 'display_name' cannot be empty or whitespace-only.")
        return value


exclude_graph_model(BaseStateEntity)
