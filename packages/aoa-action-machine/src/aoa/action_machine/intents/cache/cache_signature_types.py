# packages/aoa-action-machine/src/aoa/action_machine/intents/cache/cache_signature_types.py
"""
The types a cache declaration's annotations must name, checked when the graph is assembled.

``params`` is annotated with the operation's own ``Params``, a name that does not exist
while its class body runs, so the types are checked when the graph's Cache node is built:
before any call is served, once per operation. Only the graph imports this module, so
it may import the model and the runtime at the top without closing an import cycle.
"""

from __future__ import annotations

import types
import typing
from collections.abc import Callable
from typing import Any, get_type_hints

from aoa.action_machine.context.context_view import ContextView
from aoa.action_machine.exceptions.aspect_signature_error import AspectSignatureError
from aoa.action_machine.intents.cache.cache_signature import RETURNS, decorator_name, handed_over
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.model.base_result import BaseResult
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.runtime.cache_entry import CacheEntry
from aoa.action_machine.runtime.cache_tag import CacheTag
from aoa.action_machine.runtime.tools_box import ToolsBox

_EXPECTED: dict[str, type] = {
    "params": BaseParams,
    "box": ToolsBox,
    "entry": CacheEntry,
    "result": BaseResult,
    "duration_ms": float,
    "ctx": ContextView,
}


def _members(annotation: Any) -> tuple[Any, ...]:
    """The members of a union, or the annotation alone."""
    if isinstance(annotation, types.UnionType) or typing.get_origin(annotation) is typing.Union:
        return tuple(typing.get_args(annotation))
    return (annotation,)


def _name_of(annotation: Any) -> str:
    return getattr(annotation, "__name__", None) or str(annotation).replace("typing.", "")


def _is_connections(annotation: Any) -> bool:
    args = typing.get_args(annotation)
    return (
        typing.get_origin(annotation) is dict
        and len(args) == 2
        and args[0] is str
        and isinstance(args[1], type)
        and issubclass(args[1], BaseResource)
    )


def _returns_ok(kind: str, annotation: Any) -> bool:
    """Whether the return annotation is the one this kind answers with, ``None`` allowed."""
    answers = [member for member in _members(annotation) if member is not None.__class__]
    if len(answers) != 1:
        return False
    answer = answers[0]
    if kind == "key":
        return answer is str
    if kind == "read":
        return isinstance(answer, type) and issubclass(answer, BaseResult)
    return typing.get_origin(answer) is list and typing.get_args(answer) == (CacheTag,)


def validate_types(kind: str, action_cls: type[Any], func: Callable[..., Any]) -> None:
    """
    Refuse annotations that resolve to something other than what the machine hands over and reads back.

    Raises:
        AspectSignatureError: an annotation cannot be resolved, or names another type.
    """
    where = f"{decorator_name(kind)}: {action_cls.__name__}.{func.__name__}"
    # The operation's own names and its nested types (``Params``, ``Result``) are found too.
    localns: dict[str, Any] = dict(vars(action_cls))
    localns[action_cls.__name__] = action_cls
    localns[action_cls.__qualname__.rpartition(".")[2]] = action_cls
    try:
        hints = get_type_hints(func, localns=localns)
    except (NameError, TypeError, AttributeError) as exc:
        raise AspectSignatureError(
            f"{where} annotates its signature with names that cannot be resolved ({exc}). "
            "Refused when the graph was assembled."
        ) from exc
    for name, expected in _EXPECTED.items():
        actual = hints.get(name)
        if actual is None:
            continue
        if not (isinstance(actual, type) and issubclass(actual, expected)):
            raise AspectSignatureError(
                f"{where} annotates '{name}' as {_name_of(actual)}, but {handed_over(kind)}: it must be "
                f"{_name_of(expected)} or a subclass of it. Refused when the graph was assembled."
            )
    connections = hints.get("connections")
    if connections is not None and not _is_connections(connections):
        raise AspectSignatureError(
            f"{where} annotates 'connections' as {_name_of(connections)}, but it must be Connections. "
            "Refused when the graph was assembled."
        )
    if not _returns_ok(kind, hints.get("return")):
        raise AspectSignatureError(
            f"{where} annotates its return as {_name_of(hints.get('return'))}, but it must return "
            f"{RETURNS[kind]}. Refused when the graph was assembled."
        )



__all__ = ["validate_types"]
