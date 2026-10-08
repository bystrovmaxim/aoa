# packages/aoa-action-machine/src/aoa/action_machine/intents/access_decide/access_decide_signature.py
"""
The signature an object check must declare — names, order and types, checked as invariants.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The object check is called by the engine, so its signature is not the developer's private
business: the step hands over four things, in one order, and reads one answer back. A
declaration that renames, reorders, leaves untyped or mistypes any of them would still run
— Python binds by position — and would fail later, somewhere the developer is not looking,
or worse: silently receive something other than they think.

Two moments, because Python makes them different:

- **decoration** — what needs no name resolution: the count, the names in order, an
  annotation on every parameter, and one on the return. A missing annotation is a mistake
  about the contract, and it is cheapest to catch where it is written.
- **assembly** — what needs the class to exist first: the resolved types. ``params`` is
  annotated with the operation's own ``Params``, a name that does not exist yet while the
  class body is being executed, so the check runs when the graph is built: before any call
  is served, and once per operation.

═══════════════════════════════════════════════════════════════════════════════
SCOPE (IN / OUT)
═══════════════════════════════════════════════════════════════════════════════

IN: the parameter names and their order, the presence of annotations, and the types those
annotations resolve to.

OUT: what the check answers — the answer vocabulary is the object step's business, and the
runtime refusal to read a non-answer is there too.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, get_type_hints

from aoa.action_machine.exceptions.declaration_structure_error import DeclarationStructureError

if TYPE_CHECKING:  # loaded while the model is still being built
    pass

_PARAMS = ("self", "params", "box", "connections")
"""The parameters the object step hands over, in the order it hands them over."""

_PARAMS_WITH_CTX = (*_PARAMS, "ctx")
"""The same, plus the trailing ``ctx`` that ``@context_requires`` adds."""

def _expected_types() -> dict[str, Any]:
    """What each parameter must be annotated with, imported when the check actually runs."""
    from aoa.action_machine.context.context_view import ContextView  # pylint: disable=import-outside-toplevel
    from aoa.action_machine.model.base_params import BaseParams  # pylint: disable=import-outside-toplevel
    from aoa.action_machine.resources.base_resource import BaseResource  # pylint: disable=import-outside-toplevel
    from aoa.action_machine.runtime.tools_box import ToolsBox  # pylint: disable=import-outside-toplevel

    return {
        "params": BaseParams,
        "box": ToolsBox,
        "connections": dict[str, BaseResource],
        "ctx": ContextView,
    }

RUNTIME_NOTE = "the object step hands over (self, params, box, connections) in that order"


def expected_names(func: Callable[..., Any]) -> tuple[str, ...]:
    """The parameter names this declaration must use, in order, given ``@context_requires``."""
    return _PARAMS_WITH_CTX if hasattr(func, "_required_context_keys") else _PARAMS


def validate_names(func: Callable[..., Any]) -> None:
    """
    Refuse a signature whose parameters are renamed or reordered.

    Raises:
        TypeError: the names, their order, or the count differ from the contract.
    """
    expected = expected_names(func)
    actual = tuple(inspect.signature(func).parameters)
    if actual != expected:
        raise DeclarationStructureError(
            f"@access_decide: method '{func.__name__}' must declare its parameters as "
            f"({', '.join(expected)}), got ({', '.join(actual)}). {RUNTIME_NOTE.capitalize()}, "
            f"and Python binds by position, so a renamed or reordered parameter would receive "
            f"something other than it says."
            + _context_hint(func, actual)
        )


def _context_hint(func: Callable[..., Any], actual: tuple[str, ...]) -> str:
    """Explain the one mistake this signature makes most often: where ``@context_requires`` goes.

    The trailing ``ctx`` and the declaration that asks for it are two halves of one thing, and
    the decorator order decides which half the other one sees: ``@context_requires`` must sit
    *under* ``@access_decide``, so that the attribute exists by the time this check runs.
    """
    declares_context = hasattr(func, "_required_context_keys")
    takes_ctx = actual[-1] == "ctx" if actual else False
    wants_ctx = len(actual) == len(_PARAMS_WITH_CTX) and actual[:-1] == _PARAMS and takes_ctx
    if wants_ctx and not declares_context:
        return (
            " This declaration takes ctx but asks for no context: put "
            "@context_requires(...) under the @access_decide decorator, not above it."
        )
    if declares_context and not takes_ctx:
        return " This declaration asked for context, so it must take the trailing ctx parameter."
    return ""


def validate_annotated(func: Callable[..., Any]) -> None:
    """
    Refuse a signature without annotations: they are the contract, not decoration.

    Raises:
        TypeError: a parameter other than ``self`` is unannotated, or the return is.
    """
    signature = inspect.signature(func)
    unannotated = [
        name
        for name, parameter in signature.parameters.items()
        if name != "self" and parameter.annotation is inspect.Parameter.empty
    ]
    if unannotated:
        raise DeclarationStructureError(
            f"@access_decide: method '{func.__name__}' must annotate every parameter it "
            f"receives; ({', '.join(unannotated)}) carry no annotation. "
            f"{RUNTIME_NOTE.capitalize()}."
        )
    if signature.return_annotation is inspect.Signature.empty:
        raise DeclarationStructureError(
            f"@access_decide: method '{func.__name__}' must annotate what it returns "
            f"(-> Verdict, or one of Allowed / Refused / Undecided)."
        )


def validate_types(action_cls: type[Any], check: Callable[..., Any]) -> None:
    """
    Refuse a signature whose annotations resolve to something other than the contract types.

    Called while the graph is assembled, because ``params`` is annotated with the
    operation's own ``Params`` — a name that does not exist while its class body runs.

    Raises:
        TypeError: an annotation cannot be resolved, or names a type the step never hands over.
    """
    try:
        hints = get_type_hints(check)
    except Exception as exc:
        raise DeclarationStructureError(
            f"@access_decide: {action_cls.__name__}.{check.__name__} annotates its signature "
            f"with names that cannot be resolved ({exc}); the signature is part of the "
            f"contract, so its annotations must be importable."
        ) from exc

    for name, expected in _expected_types().items():
        actual = hints.get(name)
        if actual is None:
            continue
        if name == "connections":
            _validate_connections(action_cls, check, actual)
        elif not (isinstance(actual, type) and issubclass(actual, expected)):
            raise DeclarationStructureError(
                f"@access_decide: {action_cls.__name__}.{check.__name__} annotates "
                f"'{name}' as {_name_of(actual)}, but {RUNTIME_NOTE}: it must be "
                f"{_name_of(expected)} or a subclass of it."
            )

    _validate_return(action_cls, check, hints.get("return"))


def _validate_connections(action_cls: type[Any], check: Callable[..., Any], actual: Any) -> None:
    """``connections`` is a mapping of connection keys to resources, not a bare dict."""
    from aoa.action_machine.resources.base_resource import BaseResource  # pylint: disable=import-outside-toplevel

    origin = getattr(actual, "__origin__", None)
    args: tuple[Any, ...] = tuple(getattr(actual, "__args__", ()))
    well_formed = (
        origin is dict
        and len(args) == 2
        and isinstance(args[0], type)
        and issubclass(args[0], str)
        and isinstance(args[1], type)
        and issubclass(args[1], BaseResource)
    )
    if well_formed:
        return
    raise DeclarationStructureError(
        f"@access_decide: {action_cls.__name__}.{check.__name__} annotates 'connections' as "
        f"{_name_of(actual)}, but {RUNTIME_NOTE}: it must be dict[str, BaseResource]."
    )


def _validate_return(action_cls: type[Any], check: Callable[..., Any], actual: Any) -> None:
    """The check answers with a verdict; anything else is not an answer it can give."""
    from aoa.action_machine.intents.access_control.verdict import Verdict  # pylint: disable=import-outside-toplevel

    members = getattr(actual, "__args__", None) if _is_union(actual) else None
    candidates = members if members else (actual,)
    if all(isinstance(one, type) and issubclass(one, Verdict) for one in candidates):
        return
    raise DeclarationStructureError(
        f"@access_decide: {action_cls.__name__}.{check.__name__} annotates its return as "
        f"{_name_of(actual)}, but an object check answers with a Verdict — Allowed, Refused "
        f"or Undecided."
    )


def _is_union(annotation: Any) -> bool:
    """Whether an annotation is a union of types (``X | Y`` or ``Union[X, Y]``)."""
    import types  # pylint: disable=import-outside-toplevel
    import typing  # pylint: disable=import-outside-toplevel

    if isinstance(annotation, types.UnionType):
        return True
    return typing.get_origin(annotation) is typing.Union


def _name_of(annotation: Any) -> str:
    """A readable name for an annotation in a message."""
    return getattr(annotation, "__name__", None) or str(annotation).replace("typing.", "")


__all__ = ["expected_names", "validate_annotated", "validate_names", "validate_types"]
