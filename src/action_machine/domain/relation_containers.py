# src/action_machine/domain/relation_containers.py
"""
Relation **containers** for entity fields: ids always, full objects optional.

Six generic types cover **ownership** (composition, aggregation, association)
times **cardinality** (one vs many). They mirror classic composition / aggregation /
association structure,
stay **frozen** like `BaseEntity`, and raise `RelationNotLoadedError` when code
reaches through a container for related data that was never hydrated.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Express how entities link to each other in the type system while keeping a clear
split between **identity** (always stored) and **hydration** (optional `entity` /
`entities`). Adapters can load only ids; domain code that needs attributes must
load full rows or accept `RelationNotLoadedError`.

═══════════════════════════════════════════════════════════════════════════════
SCOPE (IN / OUT)
═══════════════════════════════════════════════════════════════════════════════

**In scope**
    Storing related ids and optional object graphs for One/Many shapes.
    Attribute **proxying** on One containers (`customer_ref.name` → `entity.name`).
    Indexing, slicing, iteration on Many over **loaded** `entities` only.
    Immutability after construction.

**Out of scope**
    Lazy loading or automatic fetches — see `RelationNotLoadedError` in
    `exceptions.py`.
    Enforcing the inverse-side **compatibility matrix** — ``GateCoordinator``
    validates `Inverse` / `Rel` pairings at **build** time, not inside these
    containers.
    Choosing id types (``str``, ``int``, ``UUID``, …) — whatever the target
    entity uses.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

**One** (`CompositeOne`, `AggregateOne`, `AssociationOne`)::

    id: Any              — always set
    entity: T | None     — optional hydrated row
    other attrs          — proxied to `entity` if set, else RelationNotLoadedError

**Many** (`CompositeMany`, …)::

    ids: tuple[Any, ...]      — always (possibly empty)
    entities: tuple[T, ...]   — hydrated rows (possibly empty)
    entities_loaded: bool     — explicit load marker (``_entities_loaded``); when
        ``False``, empty ``entities`` means *not loaded*; when ``True``, empty means
        *loaded with zero rows*. Non-empty ``entities`` implies loaded unless
        contradicted (see ``ValueError`` in constructor).
    __getitem__ / __iter__    — ``RelationNotLoadedError`` if not loaded; if loaded,
        empty ``entities`` yields empty iteration / normal ``IndexError`` on bad index

::

    repository / adapter
         │
         ├─ full row(s)     ──>  AssociationOne(id=…, entity=obj)
         │
         └─ ids only        ──>  AssociationOne(id=…)
                                    │
                                    └─> ref.name  ──> RelationNotLoadedError

═══════════════════════════════════════════════════════════════════════════════
OWNERSHIP × CARDINALITY MATRIX
═══════════════════════════════════════════════════════════════════════════════

+-------------------+----------------------------------+
| Type              | Role                             |
+===================+==================================+
| `CompositeOne`    | one child, strong ownership      |
| `CompositeMany`   | many children, strong ownership  |
| `AggregateOne`    | one child, weak ownership        |
| `AggregateMany`   | many children, weak ownership    |
| `AssociationOne`  | one peer, no ownership           |
| `AssociationMany` | many peers, no ownership         |
+-------------------+----------------------------------+

**Inverse compatibility** (checked at coordinator build, not here): composite or
aggregate on one side pairs with **association** on the other; composite↔composite,
aggregate↔aggregate, composite↔aggregate are rejected.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- **One:** `id` is never `None` at construction.
- All containers are **frozen**: no `__setattr__` / `__delattr__` on instances.
- Proxy / index / iteration paths require hydrated payloads or they raise
  `RelationNotLoadedError` (message format lives in `exceptions.py`).

═══════════════════════════════════════════════════════════════════════════════
RATIONALE
═══════════════════════════════════════════════════════════════════════════════

Ids-without-rows is a normal partial-load shape; failing fast on accidental
attribute access avoids silent `None` bugs. Distinct container classes encode
ownership for static analysis and coordinator rules without a parallel string
enum everywhere. Frozen instances align with immutable entities and make relation
snapshots safe to pass through pipelines.

═══════════════════════════════════════════════════════════════════════════════
LIFECYCLE (IMPORT VS BUILD VS RUNTIME)
═══════════════════════════════════════════════════════════════════════════════

- **Import**: types and `RelationType` enum are defined.
- **Build**: coordinator validates relation declarations; containers are not
  involved in that pass.
- **Runtime**: adapters construct containers; domain code reads ids or pays
  the hydration cost before drilling into related fields.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Hydrated One container::

    ref = AssociationOne(id="CUST-001", entity=customer)
    ref.id
    ref.name   # proxies to customer.name

Ids-only One (edge)::

    ref = AssociationOne(id="CUST-001")
    ref.id
    ref.name   # RelationNotLoadedError (see exceptions.py wording)

Many with entities::

    bag = CompositeMany(ids=("A", "B"), entities=(e1, e2))
    len(bag)
    bag[0]

Many ids only (edge)::

    bag = CompositeMany(ids=("A", "B"))
    bag[0]     # RelationNotLoadedError

Loaded but zero rows::

    bag = CompositeMany(ids=(), entities=(), entities_loaded=True)
    list(bag)  # []
    bag.is_loaded  # True

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- `ValueError`: One container constructed with `id=None`; Many with
  ``entities_loaded=False`` and a non-empty ``entities`` tuple.
- `RelationNotLoadedError`: proxy/index/iter without `entity` / `entities`.
- `AttributeError`: mutation attempted on a frozen container; or proxy target
  missing attribute when `entity` is loaded.
- Message text for `RelationNotLoadedError` is centralized in
  `action_machine.domain.exceptions` — keep docs aligned there, not duplicated
  verbatim here.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Runtime relation container primitives for domain entity fields.
CONTRACT: Keep relation identity always available (id/ids) and enforce explicit hydration for object access.
INVARIANTS: Containers are frozen; unloaded relation object access fails fast via RelationNotLoadedError.
FLOW: adapter/repository builds container -> domain code reads id(s) or hydrated entity payload -> coordinator uses annotations for topology semantics.
FAILURES: ValueError on invalid constructor combinations, RelationNotLoadedError on unloaded access, AttributeError on mutation.
EXTENSION POINTS: New relation flavors can subclass BaseRelationOne/BaseRelationMany with custom relation_type semantics.
AI-CORE-END
"""

from __future__ import annotations

from collections.abc import Iterator
from enum import Enum
from typing import Any, ClassVar, TypeVar, cast, overload

from action_machine.domain.exceptions import RelationNotLoadedError

T = TypeVar("T")


class RelationType(Enum):
    """
    Ownership flavour for a relation field.

    Maps to structural relationship flavours (composition, aggregation, association):

    COMPOSITION
        Strong ownership; children do not exist without the parent; parent
        deletion removes children.

    AGGREGATION
        Weak ownership; children can exist independently; parent deletion
        detaches them.

    ASSOCIATION
        Peer link; neither side owns the other’s lifecycle.
    """

    COMPOSITION = "composition"
    AGGREGATION = "aggregation"
    ASSOCIATION = "association"


# ═════════════════════════════════════════════════════════════════════════════
# Base containers
# ═════════════════════════════════════════════════════════════════════════════


class BaseRelationOne[T]:
    """
    Base **to-one** relation container.

    **Role**
        Hold a related **id** and optionally the full **entity**. Unknown
        attribute names delegate to `entity` when hydrated.

    **Invariants**
        `id` is mandatory and non-None. Instance is immutable.

    **Neighbors**
        Subclasses only override `relation_type`. Errors for unloaded graphs use
        `RelationNotLoadedError` from `exceptions.py`.

    **Attributes**
        ``id``
            Related primary key (any type the model uses).
        ``entity``
            Hydrated row or ``None`` when only the id was loaded.
        ``relation_type``
            Set on concrete subclasses for coordinator / diagram metadata.

    AI-CORE-BEGIN
    ROLE: Base immutable to-one relation wrapper.
    CONTRACT: Always store id; optionally hold hydrated entity and proxy attributes to it.
    INVARIANTS: id is mandatory; missing hydrated entity triggers RelationNotLoadedError for proxied access.
    AI-CORE-END
    """

    __slots__ = ("_entity", "_id")

    relation_type: ClassVar[RelationType]  # pylint: disable=declare-non-slot

    def __init__(self, *, id: Any, entity: T | None = None) -> None:  # pylint: disable=redefined-builtin
        """
        Args:
            id: Related entity identifier (required).
            entity: Hydrated entity, or ``None`` if only ``id`` was loaded.

        Raises:
            ValueError: If ``id`` is ``None``.
        """
        if id is None:
            raise ValueError(
                f"{self.__class__.__name__}: id cannot be None. "
                f"A relation container must always store an identifier."
            )
        object.__setattr__(self, "_id", id)
        object.__setattr__(self, "_entity", entity)

    @property
    def id(self) -> Any:
        """Related id; always available."""
        return object.__getattribute__(self, "_id")

    @property
    def entity(self) -> T | None:
        """Hydrated related object, or ``None``."""
        return cast(T | None, object.__getattribute__(self, "_entity"))

    @property
    def is_loaded(self) -> bool:
        """True when ``entity`` is not ``None``."""
        return self._entity is not None

    def __getattr__(self, name: str) -> Any:
        """
        Forward attribute access to ``entity`` when it is loaded.

        ``id``, ``entity``, ``is_loaded``, ``relation_type``, and ``__slots__``
        fields are resolved without entering this hook.

        Args:
            name: Attribute requested on the container.

        Returns:
            Attribute value from ``entity``.

        Raises:
            RelationNotLoadedError: ``entity`` is ``None`` (see ``exceptions.py``).
            AttributeError: ``entity`` is set but has no such attribute.
        """
        entity = object.__getattribute__(self, "_entity")
        if entity is None:
            entity_id = object.__getattribute__(self, "_id")
            raise RelationNotLoadedError(
                container_class_name=self.__class__.__name__,
                attribute_name=name,
                entity_id=entity_id,
            )
        return getattr(entity, name)

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError(
            f"{self.__class__.__name__} is frozen; assigning to '{name}' is not allowed."
        )

    def __delattr__(self, name: str) -> None:
        raise AttributeError(
            f"{self.__class__.__name__} is frozen; deleting '{name}' is not allowed."
        )

    def __repr__(self) -> str:
        entity = object.__getattribute__(self, "_entity")
        entity_id = object.__getattribute__(self, "_id")
        loaded = "loaded" if entity is not None else "id_only"
        return f"{self.__class__.__name__}(id={entity_id!r}, {loaded})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BaseRelationOne):
            return NotImplemented
        return self.id == other.id and type(self) is type(other)

    def __hash__(self) -> int:
        return hash((type(self), self.id))


class BaseRelationMany[T]:
    """
    Base **to-many** relation container.

    **Role**
        Hold ``ids`` and optionally parallel ``entities``; support ``len``,
        indexing, slicing, and iteration over loaded rows.

    **Invariants**
        Immutable instance. Indexing and iteration require
        ``entities_loaded`` (hydration completed). If not loaded, they raise
        `RelationNotLoadedError`. If loaded with zero entities, iteration is
        empty and out-of-range index raises `IndexError`.

    **Neighbors**
        Concrete classes set `relation_type`. Coordinator validates pairing with
        inverse side at build time.

    AI-CORE-BEGIN
    ROLE: Base immutable to-many relation wrapper.
    CONTRACT: Track ids plus optional hydrated entities with explicit loaded-state semantics.
    INVARIANTS: Index/iteration require loaded entities; unloaded access fails fast.
    AI-CORE-END
    """

    __slots__ = ("_entities", "_entities_loaded", "_ids")

    relation_type: ClassVar[RelationType]  # pylint: disable=declare-non-slot

    def __init__(
        self,
        *,
        ids: tuple[Any, ...] = (),
        entities: tuple[T, ...] = (),
        entities_loaded: bool | None = None,
    ) -> None:
        """
        Args:
            ids: Related identifiers (may be empty).
            entities: Hydrated rows (may be empty).
            entities_loaded: If ``True``, ``entities`` is the result of a load (empty
                means zero related rows). If ``False``, relation is not hydrated.
                If ``None``, inferred as ``True`` iff ``entities`` is non-empty.
        """
        if entities_loaded is False and len(entities) > 0:
            raise ValueError(
                "entities_loaded=False is incompatible with a non-empty entities tuple",
            )
        if entities_loaded is None:
            loaded = len(entities) > 0
        else:
            loaded = entities_loaded

        object.__setattr__(self, "_ids", ids)
        object.__setattr__(self, "_entities", entities)
        object.__setattr__(self, "_entities_loaded", loaded)

    @property
    def ids(self) -> tuple[Any, ...]:
        """Tuple of related ids."""
        return cast(tuple[Any, ...], object.__getattribute__(self, "_ids"))

    @property
    def entities(self) -> tuple[T, ...]:
        """Tuple of hydrated entities (possibly empty)."""
        return cast(tuple[T, ...], object.__getattribute__(self, "_entities"))

    @property
    def is_loaded(self) -> bool:
        """True when the ``entities`` tuple reflects a completed load (may be empty)."""
        return bool(object.__getattribute__(self, "_entities_loaded"))

    def __len__(self) -> int:
        """Number of ids (not necessarily loaded entities)."""
        return len(self.ids)

    @overload
    def __getitem__(self, index: int) -> T: ...

    @overload
    def __getitem__(self, index: slice) -> tuple[T, ...]: ...

    def __getitem__(self, index: int | slice) -> T | tuple[T, ...]:
        """
        Args:
            index: Integer index or slice over ``entities``.

        Returns:
            One entity or a tuple slice.

        Raises:
            RelationNotLoadedError: Relation not hydrated.
            IndexError: Loaded but index out of range (including empty ``entities``).
        """
        if not bool(object.__getattribute__(self, "_entities_loaded")):
            raise RelationNotLoadedError(
                container_class_name=self.__class__.__name__,
                attribute_name=f"[{index}]",
                entity_id=self.ids,
            )
        entities = self.entities
        result = entities[index]
        if isinstance(index, slice):
            return cast(tuple[T, ...], result)
        return cast(T, result)

    def __iter__(self) -> Iterator[T]:
        """
        Yields hydrated entities in order.

        Raises:
            RelationNotLoadedError: Relation not hydrated.
        """
        if not bool(object.__getattribute__(self, "_entities_loaded")):
            raise RelationNotLoadedError(
                container_class_name=self.__class__.__name__,
                attribute_name="__iter__",
                entity_id=self.ids,
            )
        return iter(self.entities)

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError(
            f"{self.__class__.__name__} is frozen; assigning to '{name}' is not allowed."
        )

    def __delattr__(self, name: str) -> None:
        raise AttributeError(
            f"{self.__class__.__name__} is frozen; deleting '{name}' is not allowed."
        )

    def __repr__(self) -> str:
        count = len(self.ids)
        n_ent = len(self.entities)
        flag = "yes" if self.is_loaded else "no"
        return f"{self.__class__.__name__}(count={count}, entities_loaded={flag}, n_entities={n_ent})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BaseRelationMany):
            return NotImplemented
        return self.ids == other.ids and type(self) is type(other)

    def __hash__(self) -> int:
        return hash((type(self), self.ids))


# ═════════════════════════════════════════════════════════════════════════════
# Composition
# ═════════════════════════════════════════════════════════════════════════════


class CompositeOne(BaseRelationOne[T]):
    """
    To-one **composition** (strong ownership).

    The child cannot exist without the parent in domain terms; inverse side
    should be modeled as **association**. Coordinator enforces the compatibility
    matrix at build time.

    Example::

        shipping_address: Annotated[
            CompositeOne[AddressEntity],
            Inverse(AddressEntity, "order"),
        ] = Rel(description="Delivery address")
    """

    relation_type = RelationType.COMPOSITION


class CompositeMany(BaseRelationMany[T]):
    """
    To-many **composition** (strong ownership).

    Example::

        items: Annotated[
            CompositeMany[OrderItemEntity],
            Inverse(OrderItemEntity, "order"),
        ] = Rel(description="Line items")
    """

    relation_type = RelationType.COMPOSITION


# ═════════════════════════════════════════════════════════════════════════════
# Aggregation
# ═════════════════════════════════════════════════════════════════════════════


class AggregateOne(BaseRelationOne[T]):
    """
    To-one **aggregation** (weak ownership).

    Example::

        leader: Annotated[
            AggregateOne[EmployeeEntity],
            Inverse(EmployeeEntity, "led_team"),
        ] = Rel(description="Team lead")
    """

    relation_type = RelationType.AGGREGATION


class AggregateMany(BaseRelationMany[T]):
    """
    To-many **aggregation** (weak ownership).

    Example::

        members: Annotated[
            AggregateMany[EmployeeEntity],
            Inverse(EmployeeEntity, "team"),
        ] = Rel(description="Team members")
    """

    relation_type = RelationType.AGGREGATION


# ═════════════════════════════════════════════════════════════════════════════
# Association
# ═════════════════════════════════════════════════════════════════════════════


class AssociationOne(BaseRelationOne[T]):
    """
    To-one **association** (no ownership).

    Pairs with composite, aggregate, or another association on the inverse.

    Example::

        customer: Annotated[
            AssociationOne[CustomerEntity],
            Inverse(CustomerEntity, "orders"),
        ] = Rel(description="Customer who placed the order")
    """

    relation_type = RelationType.ASSOCIATION


class AssociationMany(BaseRelationMany[T]):
    """
    To-many **association** (no ownership).

    Example::

        orders: Annotated[
            AssociationMany[OrderEntity],
            Inverse(OrderEntity, "customer"),
        ] = Rel(description="Customer orders")
    """

    relation_type = RelationType.ASSOCIATION
