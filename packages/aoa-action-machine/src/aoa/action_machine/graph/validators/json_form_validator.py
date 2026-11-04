# packages/aoa-action-machine/src/aoa/action_machine/graph/validators/json_form_validator.py
"""
JsonFormValidator — refuse a Params or Result that has no JSON Schema, and name the field.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Every Params and Result goes out as JSON through an adapter or the cache, and its
JSON Schema is what FastAPI and MCP publish. A field whose type has no JSON form
(a plain Python class) would fail only when something writes the value, on a live
request. The build refuses it instead, in validation and in serialization mode,
naming ``<Class qualname>.<field>`` and the fix. The pass only reads: no node and
no edge change.

═══════════════════════════════════════════════════════════════════════════════
DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    graph nodes -> node_obj a BaseParams / BaseResult subclass
                     |
                     +--> model_json_schema(mode=...) for "validation" and "serialization"
                            fails -> the first field whose own schema fails -> JsonFormError
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, PydanticUserError, TypeAdapter

from aoa.action_machine.graph.core.exceptions import InvalidGraphError
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.model.base_result import BaseResult

__all__ = ["JsonFormError", "validate_json_forms"]

_Mode = Literal["validation", "serialization"]
_MODES: tuple[_Mode, ...] = ("validation", "serialization")
_FIX = "Describe it with JsonSchemaValue, or leave it out of the {kind}."


class JsonFormError(InvalidGraphError):
    """
    AI-CORE-BEGIN
    ROLE: Build refusal of a Params or Result whose JSON Schema cannot be built.
    CONTRACT: Message starts ``<Class qualname>.<field> has no JSON form (<mode> mode)`` and says how to fix it.
    AI-CORE-END
    """


def _schema_error(build: Any, mode: _Mode) -> Exception | None:
    """Return the error ``build(mode=mode)`` raises while building a JSON Schema, or ``None`` when it builds."""
    try:
        build(mode=mode)
    except (PydanticUserError, TypeError, ValueError) as exc:  # PydanticInvalidForJsonSchema is a PydanticUserError
        return exc
    return None


def _failing_field(host: type[BaseModel], mode: _Mode) -> tuple[str, Exception] | None:
    """Return the first field whose own JSON Schema fails in ``mode``, with the error."""
    for name, field in host.model_fields.items():
        annotation: Any = field.annotation
        if field.metadata:
            annotation = Annotated[(annotation, *field.metadata)]
        adapter = TypeAdapter(annotation, config=ConfigDict(arbitrary_types_allowed=True))
        error = _schema_error(adapter.json_schema, mode)
        if error is not None:
            return name, error
    return None


def _first_line(error: Exception) -> str:
    return str(error).strip().splitlines()[0]


def _check(host: type[BaseModel]) -> None:
    """Refuse ``host`` when its JSON Schema fails in either mode, naming the field when one fails alone."""
    kind = "Params" if issubclass(host, BaseParams) else "Result"
    for mode in _MODES:
        error = _schema_error(host.model_json_schema, mode)
        if error is None:
            continue
        found = _failing_field(host, mode)
        where = f"{host.__qualname__}.{found[0]}" if found else host.__qualname__
        reason = _first_line(found[1] if found else error)
        raise JsonFormError(f"{where} has no JSON form ({mode} mode): {reason}. {_FIX.format(kind=kind)}")


def validate_json_forms(nodes: Iterable[Any]) -> None:
    """Check every Params and Result among ``nodes``."""
    for node in nodes:
        host = node.node_obj
        if isinstance(host, type) and issubclass(host, (BaseParams, BaseResult)):
            _check(host)
