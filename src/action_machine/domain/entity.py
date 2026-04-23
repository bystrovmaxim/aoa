# src/action_machine/domain/entity.py
"""
Abstract base for all domain entities in ActionMachine.

`BaseEntity` defines the in-memory domain object contract: typed fields,
immutability, strict structure, and optional partial loads from storage. It is
**not** a transport schema; use Params/Result or explicit DTOs for wire formats.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Entities are the **internal** representation of domain objects. They stay free of
I/O: no SQL, HTTP, or filesystem. Adapters and resource managers load data and
construct entities; the type itself does not know *where* data came from.

═══════════════════════════════════════════════════════════════════════════════
SCOPE (IN / OUT)
═══════════════════════════════════════════════════════════════════════════════

**In scope for this module**
    Class-level naming invariant (`*Entity` suffix).
    Pydantic model config: `frozen=True`, `extra="forbid"`.
    Partial construction via `partial()` and fail-fast access via `__getattr__`.
    Mixins `EntityIntent` and `DescribedFieldsIntent` so `@entity` and
    non-empty `Field(description=...)` are part of the entity contract.

**Out of scope (by design)**
    Persistence queries, caching, and lazy loading — partial instances never
    fetch missing fields.
    API schemas, OpenAPI, or RPC payloads — use separate DTOs when needed.
    Coordinator graph construction — lives in metadata inspectors and
    `GraphCoordinator.build()`, not in this file.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

Inheritance (simplified):

    BaseModel (Pydantic)
        └── BaseSchema          — dict-like access, dot-path `resolve()`
                └── BaseEntity (ABC)
                        + EntityIntent           — declares `@entity` grammar
                        + DescribedFieldsIntent  — non-empty field descriptions

Coordinator-facing flow (conceptual):

    @entity  ──writes──>  _entity_info  (scratch)
         │
         ▼
    EntityIntentInspector  ──reads model + scratch──>  facet payloads / graph
         │
         ▼
    GraphCoordinator  (after `build()`)

Partial load vs full construction:

    Adapter / repository
         │
         ├─ all required fields + validation ──>  OrderEntity(...)
         │
         └─ subset only ──>  OrderEntity.partial(id=..., amount=...)
                                    │
                                    ▼
                            __getattr__ on missing **model** field
                                    │
                                    └─> FieldNotLoadedError (not lazy I/O)

═══════════════════════════════════════════════════════════════════════════════
RATIONALE
═══════════════════════════════════════════════════════════════════════════════

Immutability and `extra="forbid"` reduce accidental mutation and typo-driven
schema drift in long action pipelines. Splitting **entity** types from **API**
types avoids leaking persistence shapes and partial-load internals to clients.
`partial()` skips validation intentionally: the loader is trusted to supply
consistent subsets; raising on first read of a missing field surfaces bugs
immediately without hidden queries. Mixing intent markers into the base class keeps
the rule “only entities use `@entity`” enforceable via `issubclass` at decorator
time rather than ad hoc checks.

═══════════════════════════════════════════════════════════════════════════════
LIFECYCLE (IMPORT VS BUILD VS RUNTIME)
═══════════════════════════════════════════════════════════════════════════════

- **Import / class body**: `__init_subclass__` enforces the `Entity` suffix;
  `@entity` runs and sets `_entity_info`; Pydantic builds `model_fields`.
- **Coordinator `build()`**: inspectors validate lifecycles, descriptions,
  relations, and graph consistency — **not** in this module.
- **Runtime**: normal construction validates types; `partial()` does not;
  attribute access on partial instances may raise `FieldNotLoadedError`.

"""

from __future__ import annotations

from abc import ABC
from typing import Any, ClassVar, Self

from pydantic import ConfigDict

from action_machine.domain.exceptions import FieldNotLoadedError
from action_machine.intents.entity.entity_intent import EntityIntent
from action_machine.legacy.described_fields.marker import DescribedFieldsIntent
from action_machine.model.base_schema import BaseSchema
from action_machine.exceptions import NamingSuffixError

# Suffix required for every class that inherits BaseEntity (directly or indirectly).
_REQUIRED_SUFFIX = "Entity"


class BaseEntity(BaseSchema, ABC, EntityIntent, DescribedFieldsIntent):
    """
AI-CORE-BEGIN
    ROLE: Shared entity base with strict runtime access semantics.
    CONTRACT: Provides immutable model behavior plus controlled partial-load mechanics.
    INVARIANTS: Missing model fields on partial instances fail fast via ``FieldNotLoadedError``.
    AI-CORE-END
"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    # Typing hook; `@entity` sets this on concrete classes.
    _entity_info: ClassVar[dict[str, Any]]

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """
        Enforce the ``*Entity`` naming invariant when a subclass is defined.

        Called by Python for every direct or indirect subclass of `BaseEntity`.

        Args:
            **kwargs: Forwarded to `type.__init_subclass__`.

        Raises:
            NamingSuffixError: If ``cls.__name__`` does not end with ``Entity``.
        """
        super().__init_subclass__(**kwargs)

        if not cls.__name__.endswith(_REQUIRED_SUFFIX):
            raise NamingSuffixError(
                f"Class '{cls.__name__}' inherits from BaseEntity but its name must "
                f"end with the suffix '{_REQUIRED_SUFFIX}'. "
                f"Rename it to '{cls.__name__}{_REQUIRED_SUFFIX}'."
            )

    @classmethod
    def partial(cls, **kwargs: Any) -> Self:
        """
        Build a **partial** entity without Pydantic validation.

        Uses `model_construct()` so type checks and required-field rules are
        skipped — callers that load from storage are responsible for consistency.
        Sets `_partial_instance=True` and `_loaded_fields=frozenset(kwargs)` via
        `object.__setattr__` to satisfy `frozen` instances.

        Args:
            **kwargs: Field names and values present in this load.

        Returns:
            An instance with only the given fields materialized in ``__dict__``.

        Raises:
            Does not validate; invalid combinations may only surface later on
            access or when merging into a full instance.

        Example:
            ``OrderEntity.partial(id="ORD-001", amount=1500.0)`` — reading
            ``status`` raises `FieldNotLoadedError`.
        """
        instance = cls.model_construct(**kwargs)
        object.__setattr__(instance, "_partial_instance", True)
        object.__setattr__(instance, "_loaded_fields", frozenset(kwargs.keys()))
        return instance

    def __getattr__(self, name: str) -> Any:
        """
        Handle access to **declared** fields that were not passed to `partial()`.

        Pydantic invokes this only when `object.__getattribute__` does not find
        ``name``. Fully constructed instances store all fields in ``__dict__``,
        so this path is mainly for partial instances.

        Args:
            name: Attribute name.

        Returns:
            Never returns for a missing partial field; see Raises.

        Raises:
            FieldNotLoadedError: ``name`` is a model field, the instance is
                partial, and ``name`` was not in `_loaded_fields`.
            AttributeError: ``name`` is not a model field (standard object
                semantics).
        """
        if name in self.__class__.model_fields:
            try:
                is_partial = object.__getattribute__(self, "_partial_instance")
            except AttributeError:
                is_partial = False

            if is_partial:
                loaded = object.__getattribute__(self, "_loaded_fields")
                raise FieldNotLoadedError(
                    field_name=name,
                    entity_class_name=self.__class__.__name__,
                    loaded_fields=loaded,
                )

        raise AttributeError(
            f"'{self.__class__.__name__}' object has no attribute '{name}'"
        )
