# packages/aoa-action-machine/src/aoa/action_machine/model/json_schema_value.py
"""
JsonSchemaValue — Pydantic v2 type factory for JSON fields validated by JSON Schema.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``JsonSchemaValue`` is a **field-level** type for ``BaseResult``, ``BaseParams``, or any
``BaseModel``. Use it when one field must hold JSON that is validated against a
**static, strict JSON Schema** at model construction time (graph payloads, audit trails,
metadata blobs, interchange snapshots) while the rest of the model stays fully typed with
ordinary Pydantic fields. :meth:`JsonSchemaValue.define` rejects schemas that allow unknown
keys on objects or omit ``items`` on arrays.

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

Strict object + arrays (each ``items`` subschema is explicit)::

    EMPTY_OBJECT = {"type": "object", "properties": {}, "additionalProperties": False}
    GRAPH_SCHEMA = {
        "type": "object",
        "properties": {
            "nodes": {"type": "array", "items": EMPTY_OBJECT},
            "edges": {"type": "array", "items": EMPTY_OBJECT},
        },
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
- **``define()`` schema document:** invalid JSON Schema raises ``jsonschema.SchemaError``; schemas
  that violate strict-shape rules raise ``ValueError`` before ``check_schema``.
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


def _schema_type_includes(node: Mapping[str, Any], token: str) -> bool:
    """True if Draft-7 ``type`` on ``node`` is ``token`` or a list/tuple containing ``token``."""
    t = node.get("type")
    if isinstance(t, str):
        return t == token
    if isinstance(t, (list, tuple)):
        return any(x == token for x in t if isinstance(x, str))
    return False


_COMBINATOR_KEYS: tuple[str, ...] = ("oneOf", "anyOf", "allOf")


def _enforce_strict_alternatives(alts: Any, alt_key: str, path: str) -> None:
    if not isinstance(alts, (list, tuple)):
        msg = f"JsonSchemaValue strict schema: {path}.{alt_key} must be a list of subschemas."
        raise ValueError(msg)
    for idx, sub in enumerate(alts):
        if isinstance(sub, Mapping):
            _enforce_strict_json_schema(sub, path=f"{path}.{alt_key}[{idx}]")


def _enforce_strict_object_branch(node: Mapping[str, Any], path: str) -> None:
    props = node.get("properties")
    if not isinstance(props, dict):
        msg = f"JsonSchemaValue strict schema: object at {path} must declare 'properties' as an object."
        raise ValueError(msg)
    if node.get("additionalProperties") is not False:
        msg = (
            f"JsonSchemaValue strict schema: object at {path} must set "
            f'"additionalProperties": false (got {node.get("additionalProperties", "MISSING")!r}).'
        )
        raise ValueError(msg)
    for prop_name, sub_schema in props.items():
        if not isinstance(sub_schema, Mapping):
            msg = (
                f"JsonSchemaValue strict schema: {path}.properties[{prop_name!r}] "
                f"must be a mapping, got {type(sub_schema).__name__}."
            )
            raise TypeError(msg)
        _enforce_strict_json_schema(sub_schema, path=f"{path}.properties[{prop_name!r}]")


def _enforce_strict_array_items_branch(items: Any, path: str) -> None:
    if items is None:
        msg = f"JsonSchemaValue strict schema: array at {path} must declare 'items'."
        raise ValueError(msg)
    if isinstance(items, list):
        for i, sub in enumerate(items):
            if not isinstance(sub, Mapping):
                msg = (
                    f"JsonSchemaValue strict schema: {path}.items[{i}] must be a mapping, "
                    f"got {type(sub).__name__}."
                )
                raise TypeError(msg)
            _enforce_strict_json_schema(sub, path=f"{path}.items[{i}]")
        return
    if isinstance(items, Mapping):
        _enforce_strict_json_schema(items, path=f"{path}.items")
        return
    msg = (
        f"JsonSchemaValue strict schema: {path}.items must be a mapping or list of mappings, "
        f"got {type(items).__name__}."
    )
    raise TypeError(msg)


def _enforce_strict_json_schema(node: Any, *, path: str) -> None:
    """
    Require explicit, closed shapes: objects list every property and forbid extras; arrays
    declare ``items`` with a nested strict schema. Skips ``$ref`` targets (not inlined here).
    """
    if not isinstance(node, Mapping):
        raise TypeError(
            f"JsonSchemaValue strict schema: expected a mapping at {path}, got {type(node).__name__}.",
        )
    schema_node: Mapping[str, Any] = node
    if "$ref" in schema_node:
        return

    hit_alt = next((k for k in _COMBINATOR_KEYS if k in schema_node), None)
    if hit_alt is not None:
        _enforce_strict_alternatives(schema_node[hit_alt], hit_alt, path)
        return

    not_sub = schema_node.get("not")
    if isinstance(not_sub, Mapping):
        _enforce_strict_json_schema(not_sub, path=f"{path}.not")
        return

    props = schema_node.get("properties")
    has_properties = isinstance(props, dict)
    if has_properties and not _schema_type_includes(schema_node, "object"):
        msg = (
            f"JsonSchemaValue strict schema: {path} uses 'properties' but must set "
            f"\"type\": \"object\" (explicit typing)."
        )
        raise ValueError(msg)

    if _schema_type_includes(schema_node, "object"):
        _enforce_strict_object_branch(schema_node, path)
    if _schema_type_includes(schema_node, "array"):
        _enforce_strict_array_items_branch(schema_node.get("items"), path)


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
    CONTRACT: ``define`` returns a new type; instances validate via jsonschema; ``define`` rejects
              loose object/array shapes; ``model_dump()`` returns raw JSON; ``model_json_schema()`` exposes the user schema for the field.
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
        _enforce_strict_json_schema(frozen_schema, path="$")
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
