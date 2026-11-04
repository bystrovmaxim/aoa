# packages/aoa-action-machine/src/aoa/action_machine/model/full_entities.py
"""
A field of Params or Result typed by an entity carries a full entity.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A partial entity in a field typed by the entity would leave out fields the
field's published schema requires, and the JSON it writes could not be read
back. ``BaseParams`` and ``BaseResult`` refuse it after validation, for a value
and for each item of a list or tuple, and point to a projection,
``Entity.schema(...)``, which is the field for a part. A projection's own field
holds a partial entity by design; its marker says so (``holds_partial_entity``),
and its field is skipped.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    BaseParams / BaseResult  model_validator(mode="after")
          |
          +--> refuse_partial_entities(model)
                 for each field not marked holds_partial_entity:
                   value, or each item of a list/tuple
                   a model missing a declared field  ->  ValueError naming the field
"""

from __future__ import annotations

from typing import Any, get_args

from pydantic import BaseModel


def _is_partial(value: Any) -> bool:
    """True for a model that does not hold every field it declares (``Entity.partial(...)``)."""
    if not isinstance(value, BaseModel):
        return False
    held = object.__getattribute__(value, "__dict__")
    return any(name not in held for name in type(value).model_fields)


def _marks_partial(annotation: Any) -> bool:
    """True when an annotation, or a type inside it (``X | None``, ``list[X]``), carries a projection marker."""
    if any(getattr(meta, "holds_partial_entity", False) for meta in getattr(annotation, "__metadata__", ())):
        return True
    return any(_marks_partial(argument) for argument in get_args(annotation))


def _holds_partial_by_design(field: Any) -> bool:
    """True for a projection field, whose marker declares that it holds a partial entity."""
    if any(getattr(meta, "holds_partial_entity", False) for meta in field.metadata):
        return True
    return _marks_partial(field.annotation)


def refuse_partial_entities(model: BaseModel) -> None:
    """
    Refuse a partial entity in a field that is not a projection.

    Raises:
        ValueError: names the field, the entity, what it holds, and the projection to declare.
    """
    for name, field in type(model).model_fields.items():
        if _holds_partial_by_design(field):
            continue
        value = model.__dict__.get(name)
        items = value if isinstance(value, (list, tuple)) else (value,)
        for item in items:
            if _is_partial(item):
                entity_name = type(item).__name__
                held = object.__getattribute__(item, "__dict__")
                loaded = ", ".join(field_name for field_name in type(item).model_fields if field_name in held)
                raise ValueError(
                    f"{name}: {entity_name} is partial (loaded: {loaded or 'nothing'}); this field takes a full "
                    f"entity. Declare a projection with {entity_name}.schema(...)."
                )
