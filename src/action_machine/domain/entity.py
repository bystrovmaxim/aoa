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
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Every concrete subclass name **must** end with `"Entity"` (checked in
  `__init_subclass__`); violation → `NamingSuffixError` at **class definition** time.
- Instances are **immutable** (`frozen=True`); updates use `model_copy(update=...)`.
- No undeclared fields (`extra="forbid"`).
- Each declared field uses `Field(description="...")` with a non-empty description
  (enforced when the entity is wired through the coordinator / described-fields
  pipeline — see `DescribedFieldsIntent` and inspectors).
- Concrete entities should be decorated with `@entity(...)` so `_entity_info`
  exists for the coordinator; without it, entity discovery in the graph fails.

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

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path — full load and copy-on-update::

    order = OrderEntity(id="ORD-001", amount=100.0, status="new")
    order["id"]                     # dict-like
    updated = order.model_copy(update={"status": "shipped"})

Edge — partial instance, missing field::

    order = OrderEntity.partial(id="ORD-001", amount=100.0)
    order.id        # OK
    order.status    # FieldNotLoadedError (not lazy-loaded)

Edge — bad class name (fails when the class statement runs)::

    class Order(BaseEntity):
        pass
    # NamingSuffixError: name must end with 'Entity'

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- `NamingSuffixError`: subclass name does not end with `"Entity"`.
- `FieldNotLoadedError`: on a `partial()` instance, reading a model field that
  was not passed into `partial()`.
- `AttributeError`: unknown attribute name (same message style as Pydantic).
- `model_dump()` on partial instances only includes loaded fields; serializing
  for external APIs may still need DTOs and explicit handling of relations.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Domain entity base contract.
CONTRACT: Enforce immutable strict entities with optional partial construction semantics.
INVARIANTS: ``*Entity`` naming, frozen models, forbid extra fields, and intent marker participation.
FLOW: class declaration + decorator scratch -> inspector/coordinator validation -> runtime full/partial access semantics.
FAILURES: NamingSuffixError at class definition; FieldNotLoadedError on missing fields in partial instances.
EXTENSION POINTS: Applications define concrete entities via subclassing and optional ``@entity`` metadata.
AI-CORE-END

═══════════════════════════════════════════════════════════════════════════════
LONGER ILLUSTRATION (DOMAIN + LIFECYCLE)
═══════════════════════════════════════════════════════════════════════════════

    from pydantic import Field
    from action_machine.domain import BaseEntity, BaseDomain, Lifecycle
    from action_machine.intents.entity.entity_decorator import entity

    class ShopDomain(BaseDomain):
        name = "shop"
        description = "Online store"

    @entity(description="Customer order", domain=ShopDomain)
    class OrderEntity(BaseEntity):
        lifecycle = (
            Lifecycle("Order lifecycle")
            .state("new", "New").to("confirmed", "cancelled").initial()
            .state("confirmed", "Confirmed").to("shipped").intermediate()
            .state("shipped", "Shipped").to("delivered").intermediate()
            .state("delivered", "Delivered").final()
            .state("cancelled", "Cancelled").final()
        )

        id: str = Field(description="Order identifier")
        amount: float = Field(description="Order total", ge=0)
        status: str = Field(description="Current order status")
        currency: str = Field(default="USD", description="ISO 4217 currency code")

    # Full load — validation applies:
    order = OrderEntity(id="ORD-001", amount=1500.0, status="new")
    order["id"]
    order.resolve("amount")
    order.model_dump()

    # Partial load — no validation; missing fields error on access:
    order = OrderEntity.partial(id="ORD-001", amount=1500.0)
    order.status  # FieldNotLoadedError

    # Immutability — new instance instead of mutation:
    updated = order.model_copy(update={"status": "confirmed"})
"""

from __future__ import annotations

from abc import ABC
from typing import Any, ClassVar, Self

from pydantic import ConfigDict

from action_machine.domain.exceptions import FieldNotLoadedError
from action_machine.legacy.described_fields.marker import DescribedFieldsIntent
from action_machine.legacy.entity_intent import EntityIntent
from action_machine.model.base_schema import BaseSchema
from action_machine.model.exceptions import NamingSuffixError

# Suffix required for every class that inherits BaseEntity (directly or indirectly).
_REQUIRED_SUFFIX = "Entity"


class BaseEntity(BaseSchema, ABC, EntityIntent, DescribedFieldsIntent):
    """
    Abstract base for all domain entities.

    **Role**
        Defines immutability, forbidden extras, integration with `@entity` and
        described fields, and optional partial construction for repository-style
        reads.

    **Invariants**
        - `frozen=True`, `extra="forbid"`.
        - Subclass names end with the suffix ``Entity`` (see `__init_subclass__`).
        - Partial instances set `_partial_instance` and `_loaded_fields` via
          `object.__setattr__` to bypass frozen instance protection.

    **Neighbors**
        - `BaseSchema`: dict-like access and `resolve()`.
        - `EntityIntent`: allows `@entity` on subclasses.
        - `DescribedFieldsIntent`: field descriptions required for coordinator
          validation.
        - `FieldNotLoadedError`: raised from `__getattr__` for missing partial
          fields.

    **Class / instance attributes**
        `_entity_info` (`ClassVar[dict[str, Any]]`)
            Metadata written by `@entity` (`description`, `domain`, …).

        `_partial_instance` (`bool`, instance)
            True if built with `partial()`.

        `_loaded_fields` (`frozenset[str]`, instance)
            Names supplied to `partial()`; empty for fully constructed instances.

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
