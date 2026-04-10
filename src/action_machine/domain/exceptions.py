# src/action_machine/domain/exceptions.py
"""
Exceptions for the ActionMachine **domain** subsystem (entities, relations, lifecycles).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

This module defines domain-specific exceptions. They live here (not in
`core/exceptions.py`) so the domain layer stays a **cohesive subsystem**:
core does not import domain exceptions, while domain code may still use
core errors such as `NamingSuffixError` where naming invariants are shared.

═══════════════════════════════════════════════════════════════════════════════
EXCEPTION TYPES
═══════════════════════════════════════════════════════════════════════════════

FieldNotLoadedError
    Access to an entity field that was **not** included in a partial load via
    `BaseEntity.partial()`. Subclasses `AttributeError`.

RelationNotLoadedError
    Access through a relation container (`CompositeOne`, `AssociationOne`, …)
    to attributes of the related entity when only **ids** were loaded and the
    full `entity` / `entities` payload is missing. Subclasses `AttributeError`.

EntityDecoratorError
    Violations of the `@entity` decorator contract. Subclasses `TypeError`
    (import-time / developer error).

LifecycleValidationError
    A `Lifecycle` template attached to an entity fails one of the eight
    structural integrity rules when validated during `GateCoordinator.build()`
    (via `EntityGateHostInspector` / entity lifecycle validation).
"""

from __future__ import annotations

from typing import Any


class FieldNotLoadedError(AttributeError):
    """
    Access to a field that was not loaded on a **partial** entity instance.

    Raised when code reads an attribute that was **not** passed to
    `BaseEntity.partial()`. Subclassing `AttributeError` keeps semantics
    aligned with attribute access: the field exists on the **model**, but
    not in this **instance**’s loaded subset.

    `hasattr(entity, "status")` returns `False` for a non-loaded model field
    in the partial case, which matches “attribute not available on this object.”

    This is **not** lazy loading: there is no hidden I/O. Either the field was
    supplied at construction time or access fails immediately with a clear error.

    Attributes:
        field_name:
            Name of the field that was accessed.
        entity_class_name:
            Entity class name (for messages).
        loaded_fields:
            Frozen set of field names that *were* loaded.
    """

    def __init__(
        self,
        field_name: str,
        entity_class_name: str,
        loaded_fields: frozenset[str],
    ) -> None:
        self.field_name: str = field_name
        self.entity_class_name: str = entity_class_name
        self.loaded_fields: frozenset[str] = loaded_fields

        sorted_fields = ", ".join(sorted(loaded_fields)) if loaded_fields else "(none)"
        super().__init__(
            f"Field '{field_name}' on entity '{entity_class_name}' is not loaded. "
            f"Loaded fields: {sorted_fields}. "
            f"Use a full constructor or include '{field_name}' in partial()."
        )


class RelationNotLoadedError(AttributeError):
    """
    Access to a related entity’s attributes when the relation object is not hydrated.

    Raised by **One** containers when `__getattr__` would forward to `entity` but
    `entity is None` (only `id` is present). **Many** containers raise it when
    iteration or indexing is attempted while no `entities` were loaded.

    Subclassing `AttributeError` matches “this attribute path is not available
    on the current partially-loaded graph of objects.”

    Again: **not** lazy loading — load the related entity explicitly in your
    adapter / repository layer.

    Attributes:
        container_class_name:
            Relation container class name (e.g. `AssociationOne`).
        attribute_name:
            Requested attribute or pseudo-name (e.g. `"name"`, `"[0]"`, `"__iter__"`).
        entity_id:
            Related id (or tuple of ids for Many) for diagnostics.
    """

    def __init__(
        self,
        container_class_name: str,
        attribute_name: str,
        entity_id: Any,
    ) -> None:
        self.container_class_name: str = container_class_name
        self.attribute_name: str = attribute_name
        self.entity_id: Any = entity_id

        super().__init__(
            f"Related object in {container_class_name} is not loaded (id={entity_id!r}). "
            f"Cannot access '{attribute_name}' — only the identifier is present. "
            f"Load the related entity through your persistence / manager layer."
        )


class EntityDecoratorError(TypeError):
    """
    `@entity` was used in a way that breaks its contract.

    Typical causes:
    - Applied to something that is not a class.
    - Target class does not inherit `EntityGateHost` (usually via `BaseEntity`).
    - `description` is not a non-empty string.
    - `domain` is neither `None` nor a `BaseDomain` subclass.

    Subclasses `TypeError` because these are **developer** mistakes at class
    definition time, not invalid end-user input.
    """

    pass


class LifecycleValidationError(Exception):
    """
    A `Lifecycle` template failed structural validation.

    Raised while the coordinator graph is built (entity facet inspection), when
    a lifecycle field’s `_template` violates the eight integrity rules:

    1. Every state is tagged with `.initial()`, `.intermediate()`, or `.final()`.
    2. At least one initial state exists.
    3. At least one final state exists.
    4. Final states have no outgoing transitions.
    5. Every transition target names an existing state.
    6. Every non-final state has at least one outgoing transition.
    7. From every initial state, some final state is reachable.
    8. Every non-initial state is the target of at least one transition.

    Attributes:
        entity_name:
            Entity class name containing the invalid lifecycle field.
        field_name:
            Name of the `Lifecycle` field on that entity.
        details:
            Human-readable explanation of the violation.
    """

    def __init__(
        self,
        entity_name: str,
        field_name: str,
        details: str,
    ) -> None:
        self.entity_name: str = entity_name
        self.field_name: str = field_name
        self.details: str = details

        super().__init__(
            f"Lifecycle '{field_name}' on entity '{entity_name}' is invalid: {details}"
        )
