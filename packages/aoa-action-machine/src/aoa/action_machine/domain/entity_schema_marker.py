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
          +--> ``model_json_schema`` / OpenAPI verbatim user schema
          +--> graph inspectors (PR-4+)
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Annotated, Any, get_args, get_origin

import pydantic_core
from pydantic import GetCoreSchemaHandler, GetJsonSchemaHandler

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
              its ``$schema`` names (the newest without it); Pydantic reads hooks on this instance.
    INVARIANTS: Frozen; ``schema`` is a non-empty dict; ``entity_cls`` is the projection host class;
                equality and ``repr`` are ``entity_cls`` and ``schema`` only.
    AI-CORE-END
    """

    entity_cls: type
    schema: dict[str, Any]
    check: JsonSchemaCheck = field(init=False, compare=False, repr=False)

    def __post_init__(self) -> None:
        """Check the schema once and keep the check for the values."""
        object.__setattr__(self, "check", JsonSchemaCheck(self.schema))

    def __get_pydantic_core_schema__(
        self,
        _source: Any,
        _handler: GetCoreSchemaHandler,
    ) -> pydantic_core.CoreSchema:
        """Validate wire payloads as plain JSON objects against ``schema``."""
        check = self.check

        def validate(value: Any) -> Any:
            error = check.error_of(value)
            if error is not None:
                path = " -> ".join(str(p) for p in error.absolute_path)
                tail = f" (path: {path})" if path else ""
                msg = f"{self.entity_cls.__name__} wire projection: {error.message}{tail}"
                raise ValueError(msg) from error
            return value

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
