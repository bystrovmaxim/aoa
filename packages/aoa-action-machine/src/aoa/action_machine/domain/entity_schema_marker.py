# packages/aoa-action-machine/src/aoa/action_machine/domain/entity_schema_marker.py
"""
EntitySchemaMarker — metadata for BaseEntity JSON Schema wire projections.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``BaseEntity.schema()`` attaches this marker inside ``typing.Annotated`` so Result
and Params fields can bind semantically to an entity class while validating wire
payloads against an explicit JSON Schema dict.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    BaseEntity.schema(schema={...})
          |
          v
    Annotated[ConcreteEntity, EntitySchemaMarker(entity_cls=..., schema=...)]
          |
          v
    Pydantic ``Annotated`` metadata hooks on the marker instance
          |
          +--> ``JsonSchemaCheck`` built once, when the marker is created: the schema is
          |    checked in the draft its ``$schema`` names (the newest without it), and
          |    runtime wire dicts are checked against it
          +--> the value: ``entity_cls.partial(...)`` with the projection's fields, from an entity or a
          |    mapping, checked by the schema and by the entity's field types
          +--> ``model_json_schema`` / OpenAPI verbatim user schema
          +--> graph inspectors (PR-4+)
"""

from __future__ import annotations

import copy
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Annotated, Any, ClassVar, get_args, get_origin

import pydantic_core
from pydantic import BaseModel, GetCoreSchemaHandler, GetJsonSchemaHandler

from aoa.action_machine.domain.partial_fields import validated_partial
from aoa.action_machine.system_core.json_schema_check import JsonSchemaCheck


def entity_schema_marker_from_annotated(tp: Any) -> EntitySchemaMarker | None:
    """
    Return ``EntitySchemaMarker`` from ``typing.Annotated[..., Marker]`` if present.

    AI-CORE-BEGIN
    ROLE: Locate projection marker metadata on a field annotation without assuming layout beyond ``Annotated``.
    CONTRACT: Returns ``None`` when ``tp`` is not ``Annotated`` or carries no marker.
    INVARIANTS: Returns the first ``EntitySchemaMarker`` in metadata tuple order.
    AI-CORE-END
    """
    if get_origin(tp) is not Annotated:
        return None
    for meta in get_args(tp)[1:]:
        if isinstance(meta, EntitySchemaMarker):
            return meta
    return None


@dataclass(frozen=True)
class EntitySchemaMarker:
    """
    AI-CORE-BEGIN
    ROLE: Carry JSON Schema and entity class binding inside an Annotated field type.
    CONTRACT: Produced only by ``BaseEntity.schema()``; creating it checks ``schema`` once, in the draft
              its ``$schema`` names (the newest without it), and refuses a schema whose ``properties``
              name a key that is not a field of ``entity_cls``. The field holds ``entity_cls.partial(...)``
              with exactly the projection's fields, read from an entity of that class or from a mapping,
              checked by the schema and by the entity's field types; Pydantic reads hooks on this instance.
    INVARIANTS: Frozen; ``schema`` is a non-empty dict; ``entity_cls`` is the projection host class;
                equality and ``repr`` are ``entity_cls`` and ``schema`` only.
    AI-CORE-END
    """

    # A projection's field holds a partial entity by design; Params and Result do not refuse it (#408).
    holds_partial_entity: ClassVar[bool] = True

    entity_cls: type
    schema: dict[str, Any]
    check: JsonSchemaCheck = field(init=False, compare=False, repr=False)
    fields: tuple[str, ...] = field(init=False, compare=False, repr=False)

    def __post_init__(self) -> None:
        """Check the schema once, keep the check, and keep the entity fields the projection names."""
        name = self.entity_cls.__name__
        properties = self.schema.get("properties")
        if not isinstance(properties, dict):
            raise ValueError(f"{name}.schema(): a projection lists the fields of {name} under 'properties'.")
        unknown = sorted(str(key) for key in properties if key not in getattr(self.entity_cls, "model_fields", {}))
        if unknown:
            raise ValueError(
                f"{name}.schema(): {unknown} are not fields of {name}; a projection names only fields of its entity."
            )
        object.__setattr__(self, "check", JsonSchemaCheck(self.schema))
        # Entity declaration order, so the JSON written has the same key order on every run.
        declared = tuple(n for n in getattr(self.entity_cls, "model_fields", {}) if n in properties)
        object.__setattr__(self, "fields", declared)

    def __get_pydantic_core_schema__(
        self,
        _source: Any,
        _handler: GetCoreSchemaHandler,
    ) -> pydantic_core.CoreSchema:
        """Hold a partial entity with the projection's fields, checked by the schema and by the field types."""
        check = self.check
        entity_cls: Any = self.entity_cls
        projected = self.fields

        def refuse_if(wire: Any) -> None:
            error = check.error_of(wire)
            if error is not None:
                path = " -> ".join(str(p) for p in error.absolute_path)
                tail = f" (path: {path})" if path else ""
                msg = f"{entity_cls.__name__} wire projection: {error.message}{tail}"
                raise ValueError(msg) from error

        def validate(value: Any) -> Any:
            if issubclass(type(value), entity_cls):
                # The entity already validated its values: check their JSON form, keep the values themselves.
                held = {name: value.get_field_value(name) for name in projected if value.is_field_loaded(name)}
                refuse_if(value.model_dump(mode="json", include=set(held)))
                return entity_cls.partial(**held)
            if isinstance(value, BaseModel):
                raise ValueError(
                    f"{entity_cls.__name__} wire projection: takes a {entity_cls.__name__} or a mapping of its "
                    f"fields, got {type(value).__name__}."
                )
            refuse_if(value)
            if not isinstance(value, Mapping):
                raise ValueError(f"{entity_cls.__name__} wire projection: takes a mapping of its fields.")
            return validated_partial(entity_cls, value)

        return pydantic_core.core_schema.no_info_plain_validator_function(
            validate,
            serialization=pydantic_core.core_schema.plain_serializer_function_ser_schema(
                lambda v: v,
                info_arg=False,
            ),
        )

    def __get_pydantic_json_schema__(
        self,
        _core_schema: Any,
        _handler: GetJsonSchemaHandler,
    ) -> dict[str, Any]:
        """Expose the user JSON Schema fragment for OpenAPI and ``model_json_schema()``."""
        return copy.deepcopy(dict(self.schema))
