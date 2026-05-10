# packages/aoa-action-machine/src/aoa/action_machine/model/json_schema_value.py
"""
JsonSchemaValue — Pydantic v2 type factory for JSON fields validated by JSON Schema.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``JsonSchemaValue`` is a **field-level** type for ``BaseResult``, ``BaseParams``, or any
``BaseModel``. Use it when one field must hold arbitrary JSON that is validated against a
**static JSON Schema** at model construction time (graph payloads, audit trails, metadata
blobs, interchange snapshots) while the rest of the model stays fully typed with ordinary
Pydantic fields.

═══════════════════════════════════════════════════════════════════════════════
WHY NOT ANNOTATE THE WHOLE RESULT
═══════════════════════════════════════════════════════════════════════════════

- **Scope:** the schema applies to one field, not the entire model.
- **Adapters:** FastAPI and MCP rely on per-field ``model_json_schema()``; no adapter-specific
  branching is required for ``JsonSchemaValue`` fields on wire models.
- **Coexistence:** constrained primitives (``str``, ``int``, ``Field(ge=0)``, etc.) remain
  first-class alongside schema-backed JSON columns.

═══════════════════════════════════════════════════════════════════════════════
DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    JsonSchemaValue.define(name, schema)
          |
          v
    new type T (subclass of ``_JsonSchemaValueBase``)
          |
          +--> ``T.__get_pydantic_core_schema__`` at model class build time
          |         -> ``jsonschema.validate(instance, schema)`` on assignment
          |         -> plain serializer so ``model_dump()`` / ``model_dump_json()`` emit raw JSON
          |
          +--> ``T.__get_pydantic_json_schema__`` -> user schema dict (copy) for OpenAPI / tools
          |
          v
    ``field: T = Field(description=...)`` on ``BaseResult`` / ``BaseParams``

Graph metadata (``FieldGraphNode``) uses :func:`get_json_schema_value_metadata` on resolved
annotations (after optional-unwrapping) so interchange ``properties`` include
``json_schema_value``, ``json_schema_name``, and ``json_schema``.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Simple object field::

    GRAPH_SCHEMA = {
        "type": "object",
        "properties": {"nodes": {"type": "array"}, "edges": {"type": "array"}},
        "required": ["nodes", "edges"],
        "additionalProperties": False,
    }
    GraphJson = JsonSchemaValue.define(name="GraphJson", schema=GRAPH_SCHEMA)

    class Result(BaseResult):
        label: str
        graph: GraphJson = Field(description="Interchange graph payload")

Optional field::

    class Result(BaseResult):
        graph: GraphJson | None = None

Real adapter and sample usage: see ``tests/action_machine/adapters/json_schema_adapter_fixtures.py``
and ``aoa.maxitor.samples`` actions that expose a ``sample_audit`` field.

═══════════════════════════════════════════════════════════════════════════════
KNOWN LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

``model_construct()`` skips all validators, so JSON Schema is **not** applied there. This
matches Pydantic's general ``model_construct`` contract; use the normal constructor for validated
construction.

``None`` is accepted only when the annotation is a union with ``NoneType`` (``Optional[T]`` /
``T | None``); the custom validator is not invoked for ``None``.

Large schemas are embedded verbatim in ``model_json_schema()``, OpenAPI, and graph interchange
metadata. Define ``JsonSchemaValue`` types at **module level**, not inside class bodies, so
type identity and introspection stay stable.

═══════════════════════════════════════════════════════════════════════════════
FAILURES
═══════════════════════════════════════════════════════════════════════════════

- **Field value:** invalid JSON for the schema raises Pydantic ``ValidationError`` (the core
  validator wraps ``jsonschema.ValidationError`` as ``ValueError`` for a single error surface).
- **``define()`` schema document:** invalid JSON Schema raises ``jsonschema.SchemaError``.
- **``define()`` arguments:** ``TypeError`` if ``name`` is not a ``str`` or ``schema`` is not a
  ``Mapping``; ``ValueError`` if ``name`` is whitespace-only.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping
from typing import Any

import jsonschema
import pydantic_core
from pydantic import GetCoreSchemaHandler, GetJsonSchemaHandler

JsonValue = dict[str, Any] | list[Any] | str | int | float | bool | None


class _JsonSchemaValueBase:
    """Internal base: frozen schema plus Pydantic v2 core/json-schema hooks."""

    _json_schema: dict[str, Any]
    _type_name: str

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source_type: Any,
        handler: GetCoreSchemaHandler,
    ) -> pydantic_core.CoreSchema:
        """Validate with jsonschema; serialize as plain JSON-compatible value."""
        schema = cls._json_schema

        def validate(value: Any) -> Any:
            try:
                jsonschema.validate(instance=value, schema=schema)
            except jsonschema.ValidationError as exc:
                raise ValueError(str(exc)) from exc
            return value

        return pydantic_core.core_schema.no_info_plain_validator_function(
            validate,
            serialization=pydantic_core.core_schema.plain_serializer_function_ser_schema(
                lambda v: v,
                info_arg=False,
            ),
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        core_schema: pydantic_core.CoreSchema,
        handler: GetJsonSchemaHandler,
    ) -> dict[str, Any]:
        """Return the user-supplied JSON Schema as this field's JSON Schema fragment."""
        return dict(cls._json_schema)


class JsonSchemaValue:
    """
    AI-CORE-BEGIN
    ROLE: Factory for Pydantic v2 compatible schema-backed JSON field types.
    CONTRACT: ``define`` returns a new type; instances validate via jsonschema;
              ``model_dump()`` returns raw JSON; ``model_json_schema()`` exposes the user schema for the field.
    INVARIANTS: Input ``schema`` mapping is deep-copied; distinct types never share one dict object.
    AI-CORE-END
    """

    @classmethod
    def define(
        cls,
        *,
        name: str,
        schema: Mapping[str, Any],
    ) -> type:
        """Return a new annotation type that validates instances against ``schema`` via jsonschema."""
        if not isinstance(name, str):
            raise TypeError("JsonSchemaValue.define: name must be a str.")
        if not name.strip():
            raise ValueError("JsonSchemaValue.define: name must be a non-empty string.")
        if not isinstance(schema, Mapping):
            raise TypeError(
                f"JsonSchemaValue.define: schema must be a Mapping, got {type(schema).__name__}.",
            )

        frozen_schema = copy.deepcopy(dict(schema))
        jsonschema.Draft7Validator.check_schema(frozen_schema)

        return type(
            name,
            (_JsonSchemaValueBase,),
            {
                "_json_schema": frozen_schema,
                "_type_name": name,
            },
        )


def is_json_schema_value_type(tp: Any) -> bool:
    """
    Return True if ``tp`` is a type produced by :meth:`JsonSchemaValue.define`.

    AI-CORE-BEGIN
    ROLE: Public guard for graph / tooling that must recognize schema-backed JSON annotations.
    CONTRACT: ``False`` for non-types and for types not defined via ``JsonSchemaValue.define``.
    AI-CORE-END
    """
    if not isinstance(tp, type):
        return False
    try:
        return issubclass(tp, _JsonSchemaValueBase)
    except TypeError:
        return False


def get_json_schema_value_metadata(tp: Any) -> dict[str, Any] | None:
    """
    Return ``{"name", "schema"}`` for a ``JsonSchemaValue``-defined type, else ``None``.

    AI-CORE-BEGIN
    ROLE: Stable metadata for graph ``FieldGraphNode`` without reading private attrs outside this module.
    CONTRACT: ``schema`` is a deep copy; caller may mutate the returned dict without affecting the type.
    AI-CORE-END
    """
    if not is_json_schema_value_type(tp):
        return None
    return {
        "name": tp._type_name,
        "schema": copy.deepcopy(dict(tp._json_schema)),
    }
