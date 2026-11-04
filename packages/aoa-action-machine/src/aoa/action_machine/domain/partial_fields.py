# packages/aoa-action-machine/src/aoa/action_machine/domain/partial_fields.py
"""
Read some fields of an entity from a mapping, each by its own type, into a partial entity.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A relation's ``"entity"`` (issue #407) and a projection on input (issue #408) both
receive some fields of an entity as a mapping. Each field present is validated
by the annotation the entity declares for it, with its constraints, and the
result is ``Entity.partial(...)`` holding exactly those fields. A key the entity
does not declare is refused.

The validator of a field is built on first use and kept, so a model that names
an entity whose own annotations resolve later (an import cycle closed by
``model_rebuild``) still builds; nothing here builds the entity's schema.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    validated_partial(Entity, {"id": "o1", "total": "2"})
          |
          +--> each key declared by Entity?            else ValueError naming the keys
          +--> field_adapter(Entity, name).validate_python(value)   (built once per field)
          |
          v
    Entity.partial(id="o1", total=2.0)
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Annotated, Any

from pydantic import TypeAdapter, ValidationError

_FIELD_ADAPTERS: dict[tuple[Any, str], TypeAdapter[Any]] = {}


def annotation_of(field: Any) -> Any:
    """Return a model field's annotation with its constraints, as a type a validator can be built from."""
    if field.metadata:
        return Annotated[(field.annotation, *field.metadata)]
    return field.annotation


def field_adapter(entity_cls: Any, name: str) -> TypeAdapter[Any]:
    """Return the validator of one field of ``entity_cls``, built on first use."""
    key = (entity_cls, name)
    adapter = _FIELD_ADAPTERS.get(key)
    if adapter is None:
        adapter = TypeAdapter(annotation_of(entity_cls.model_fields[name]))
        _FIELD_ADAPTERS[key] = adapter
    return adapter


def validated_partial(entity_cls: Any, fields: Mapping[str, Any]) -> Any:
    """
    Return ``entity_cls.partial(...)`` holding ``fields``, each validated by its declared annotation.

    Raises:
        ValueError: a key is not a field of ``entity_cls``, or a value does not fit its field's type
            (the message names ``Entity.field``).
    """
    declared = entity_cls.model_fields
    undeclared = sorted(str(name) for name in fields if name not in declared)
    if undeclared:
        raise ValueError(f"{entity_cls.__name__} declares no field(s) {undeclared}.")
    validated: dict[str, Any] = {}
    # Entity declaration order, whatever order the mapping came in.
    for name in (declared_name for declared_name in declared if declared_name in fields):
        item = fields[name]
        try:
            validated[name] = field_adapter(entity_cls, name).validate_python(item)
        except ValidationError as exc:
            reasons = "; ".join(error["msg"] for error in exc.errors())
            raise ValueError(f"{entity_cls.__name__}.{name}: {reasons}") from exc
    return entity_cls.partial(**validated)
