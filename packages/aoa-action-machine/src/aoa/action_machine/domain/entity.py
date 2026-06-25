# packages/aoa-action-machine/src/aoa/action_machine/domain/entity.py
"""
Abstract base for all domain entities in ActionMachine.

`BaseEntity` defines the in-memory domain object contract: typed fields,
immutability, strict structure, and optional partial loads from storage. It is
**not** a transport schema by default; use Params/Result or explicit DTOs for wire formats.
For an explicit wire contract tied to an entity class, use ``BaseEntity.schema(schema={...})``
(``Annotated`` + :class:`~aoa.action_machine.domain.entity_schema_marker.EntitySchemaMarker`).

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
    Mixins ``EntityIntent`` so ``@entity`` and non-empty ``Field(description=...)`` policies apply.
    ``BaseEntity.schema()`` builds ``Annotated`` aliases for explicit JSON Schema wire projections.

**Out of scope (by design)**
    Persistence queries, caching, and lazy loading — partial instances never
    fetch missing fields.
    Implicit API payloads without a declared wire schema — use DTOs or ``BaseEntity.schema()``;
    Pydantic/OpenAPI integration for projections uses hooks on :class:`~aoa.action_machine.domain.entity_schema_marker.EntitySchemaMarker`.
    Interchange graph construction — lives in graph-model inspectors when
    ``NodeGraphCoordinator.build()`` runs, not in this file.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

Inheritance (simplified):

    BaseModel (Pydantic)
        └── BaseSchema          — dict-like access, dot-path `resolve()`
                └── BaseEntity (ABC)
                        + EntityIntent           — declares `@entity` grammar

Coordinator-facing flow (conceptual):

    @entity  ──writes──>  _entity_info  (scratch)
         │
         ▼
    Entity collectors + ``EntityIntentResolver``  ──reads model + scratch──> interchange metadata
         │
         ▼
    ``NodeGraphCoordinator`` interchange graph after ``build()``

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
immediately without hidden queries. The ``EntityIntent`` mixin on the base class keeps
the rule “only entities use `@entity`” enforceable via `issubclass` at decorator
time rather than ad hoc checks.

═══════════════════════════════════════════════════════════════════════════════
WIRE PROJECTIONS (`BaseEntity.schema`)
═══════════════════════════════════════════════════════════════════════════════

``BaseEntity.schema(schema={...})`` declares a **partial JSON wire** view of an entity
on ``BaseParams`` / ``BaseResult`` fields: values are plain ``dict`` objects validated
by the given JSON Schema, while the graph records an ``entity_schema`` edge to the
entity class. For when to prefer a DTO, optional-field patterns, OpenAPI/MCP notes,
and limitations, see ``docs/guide/entity-wire-projection.md``.

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

import copy
from abc import ABC
from typing import Annotated, Any, ClassVar, Self

import jsonschema
from pydantic import ConfigDict

from aoa.action_machine.domain.entity_schema_marker import EntitySchemaMarker
from aoa.action_machine.domain.exceptions import FieldNotLoadedError
from aoa.action_machine.domain.lifecycle import Lifecycle
from aoa.action_machine.domain.relation_containers import BaseRelationMany, BaseRelationOne
from aoa.action_machine.exceptions.naming_suffix_error import NamingSuffixError
from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.intents.entity.entity_intent import EntityIntent
from aoa.action_machine.model.base_schema import BaseSchema

# Suffix required for every class that inherits BaseEntity (directly or indirectly).
_REQUIRED_SUFFIX = "Entity"

_SCALAR_TYPES = (str, int, float, bool, bytes)


@exclude_graph_model
class BaseEntity(BaseSchema, ABC, EntityIntent):
    """
    AI-CORE-BEGIN
        ROLE: Domain object with no coupling to any storage backend.
        CONTRACT: Knows only its own structure and Lifecycle.
        INVARIANTS: Can be hydrated from any source.
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
    # pylint: disable-next=arguments-differ
    def schema(cls, *, schema: dict[str, Any]) -> Any:  # type: ignore[override]
        """
        Return ``Annotated[cls, EntitySchemaMarker(...)]`` for an explicit JSON Schema wire projection.

        Intentionally **not** Pydantic's ``BaseModel.schema()`` (JSON Schema of the entity model);
        entity classes use this name for wire projection annotations only (see ``docs/guide/entity-wire-projection.md``).
        """
        if not isinstance(schema, dict):
            msg = f"{cls.__name__}.schema(): schema must be a dict, got {type(schema).__name__}."
            raise TypeError(msg)
        if not schema:
            msg = f"{cls.__name__}.schema(): schema cannot be empty."
            raise ValueError(msg)
        schema_copy = copy.deepcopy(schema)
        jsonschema.Draft7Validator.check_schema(schema_copy)
        return Annotated[cls, EntitySchemaMarker(entity_cls=cls, schema=schema_copy)]

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

        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

    def is_field_loaded(self, field_name: str) -> bool:
        """True when ``field_name`` is declared and present on this instance."""
        if field_name not in self.__class__.model_fields:
            return False
        try:
            is_partial = object.__getattribute__(self, "_partial_instance")
        except AttributeError:
            is_partial = False
        if not is_partial:
            return True
        loaded = object.__getattribute__(self, "_loaded_fields")
        return field_name in loaded

    def get_field_value(self, field_name: str) -> Any:
        """Return a loaded field value without triggering hidden lazy-load."""
        if field_name not in self.__class__.model_fields:
            raise AttributeError(f"'{self.__class__.__name__}' has no field '{field_name}'")
        if not self.is_field_loaded(field_name):
            loaded_fields: frozenset[str] = frozenset()
            try:
                is_partial = object.__getattribute__(self, "_partial_instance")
                if is_partial:
                    loaded_fields = object.__getattribute__(self, "_loaded_fields")
            except AttributeError:
                pass
            raise FieldNotLoadedError(
                field_name=field_name,
                entity_class_name=self.__class__.__name__,
                loaded_fields=loaded_fields,
            )
        return object.__getattribute__(self, field_name)

    def is_field(self, field_name: str) -> bool:
        """True when the field is declared and loaded on this instance."""
        if field_name not in self.__class__.model_fields:
            return False
        return self.is_field_loaded(field_name)

    def is_fields(self, field_names: list[str] | tuple[str, ...]) -> bool:
        """Logical AND of :meth:`is_field` over all names; empty sequence is True."""
        return all(self.is_field(name) for name in field_names)

    def get_primary_key(self, loaded_only: bool = True) -> dict[str, Any]:
        """Return ``id`` when loaded (PK by convention)."""
        if "id" not in self.__class__.model_fields:
            return {}
        if loaded_only and not self.is_field_loaded("id"):
            return {}
        return {"id": self.get_field_value("id")}

    def get_foreign_keys(self, loaded_only: bool = True) -> dict[str, Any]:
        """Loaded relation containers (``BaseRelationOne`` / ``BaseRelationMany``)."""
        result: dict[str, Any] = {}
        for name in self.__class__.model_fields:
            if loaded_only and not self.is_field_loaded(name):
                continue
            value = self.get_field_value(name)
            if isinstance(value, (BaseRelationOne, BaseRelationMany)):
                result[name] = value
        return result

    def get_scalar_fields(self, loaded_only: bool = True) -> dict[str, Any]:
        """Loaded primitive values; ``id`` is PK, not scalar."""
        result: dict[str, Any] = {}
        for name in self.__class__.model_fields:
            if name == "id":
                continue
            if loaded_only and not self.is_field_loaded(name):
                continue
            value = self.get_field_value(name)
            if isinstance(value, _SCALAR_TYPES):
                result[name] = value
        return result

    def get_lifecycle_fields(self, loaded_only: bool = True) -> dict[str, Any]:
        """Loaded ``Lifecycle`` instances."""
        result: dict[str, Any] = {}
        for name in self.__class__.model_fields:
            if loaded_only and not self.is_field_loaded(name):
                continue
            value = self.get_field_value(name)
            if isinstance(value, Lifecycle):
                result[name] = value
        return result

    def get_all_fields(self, loaded_only: bool = True) -> dict[str, Any]:
        """Union of PK, FK, scalar, and lifecycle getters (disjoint keys)."""
        return {
            **self.get_primary_key(loaded_only),
            **self.get_foreign_keys(loaded_only),
            **self.get_scalar_fields(loaded_only),
            **self.get_lifecycle_fields(loaded_only),
        }
