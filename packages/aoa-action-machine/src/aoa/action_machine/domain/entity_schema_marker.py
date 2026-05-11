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
          +--> ``jsonschema.validate`` for runtime wire dicts
          +--> ``model_json_schema`` / OpenAPI verbatim user schema
          +--> graph inspectors (PR-4+)
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Annotated, Any, get_args, get_origin

import jsonschema
import pydantic_core
from pydantic import GetCoreSchemaHandler, GetJsonSchemaHandler


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
    CONTRACT: Produced only by ``BaseEntity.schema()``; Pydantic reads hooks on this instance.
    INVARIANTS: Frozen; ``schema`` is a non-empty dict; ``entity_cls`` is the projection host class.
    AI-CORE-END
    """

    entity_cls: type
    schema: dict[str, Any]

    def __get_pydantic_core_schema__(
        self,
        _source: Any,
        _handler: GetCoreSchemaHandler,
    ) -> pydantic_core.CoreSchema:
        """Validate wire payloads as plain JSON objects against ``schema``."""
        frozen_schema = self.schema

        def validate(value: Any) -> Any:
            try:
                jsonschema.validate(instance=value, schema=frozen_schema)
            except jsonschema.ValidationError as exc:
                path = " -> ".join(str(p) for p in exc.absolute_path)
                tail = f" (path: {path})" if path else ""
                msg = f"{self.entity_cls.__name__} wire projection: {exc.message}{tail}"
                raise ValueError(msg) from exc
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
