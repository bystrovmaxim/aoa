# packages/aoa-action-machine/src/aoa/action_machine/intents/aspects/aspect_signature.py
"""
The signature an aspect declaration must have — the table, and later its validators.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The four declaration decorators mark methods the machine calls itself: it hands over a
fixed set of values, in one order, and reads one answer back. What a declaration receives
is therefore the contract, and a declaration that renames, reorders or leaves untyped any
of it is not a shorter form of the same thing — it is a different, wrong one, which still
runs because Python binds by position.

This module holds the four contracts as **data**: for each decorator, the parameter names
in order, the type each of them must resolve to, and the rule its return must satisfy.
The decorators, the interchange graph nodes and the tests read the same table, so a rule
cannot drift between the place that refuses it and the place that documents it.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    @summary_aspect ──┐
    @regular_aspect ──┤
    @on_error       ──┼──▶ ASPECT_CONTRACTS[kind] ──▶ shape refusals (declaration)
    @compensate     ──┘                          └──▶ type refusals  (assembly)

Two moments, because Python makes them different: what needs no name resolution — the
count, the names in order, the presence of annotations, positional callability — is
refused where the method is written; what needs the operation's own ``Params`` and
``Result`` to exist is refused when the capability is assembled.

═══════════════════════════════════════════════════════════════════════════════
SCOPE (IN / OUT)
═══════════════════════════════════════════════════════════════════════════════

IN: the four contracts and the rules their entries must satisfy.

OUT: the validators that apply them (next to this module's stories), and what a
declaration answers at run time — that belongs to the executor and to
``ActionResultTypeError``.

═══════════════════════════════════════════════════════════════════════════════
USAGE
═══════════════════════════════════════════════════════════════════════════════

    from aoa.action_machine.intents.aspects.aspect_signature import ASPECT_CONTRACTS

    contract = ASPECT_CONTRACTS["summary_aspect"]
    contract.parameters             # ("self", "params", "state", "box", "connections")
    contract.parameters_with_ctx    # the same, plus the trailing "ctx"
    contract.expected_types["box"]  # ToolsBox
    contract.return_rule            # "operation_result"
"""

from __future__ import annotations

import inspect
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Literal, get_type_hints

from aoa.action_machine.exceptions.aspect_signature_error import AspectSignatureError

ReturnRule = Literal["operation_result", "state_fragment", "none"]
"""What a declaration's return must be: the operation's ``Result``, a state fragment, or nothing."""

_BASE_PARAMETERS: tuple[str, ...] = ("self", "params", "state", "box", "connections")
"""The parameters the pipeline hands to every aspect, in the order it hands them over."""

_COMPENSATE_PARAMETERS: tuple[str, ...] = (
    "self",
    "params",
    "state_before",
    "state_after",
    "box",
    "connections",
    "error",
)
"""The compensator's parameters: two states, because it is called after one was replaced."""

_DECLARED_MOMENT = " Refused while the class body was executing, where the declaration is written."
"""Appended to every refusal made at declaration time, so the reader knows how far the class got."""

_ASSEMBLED_MOMENT = (
    " Refused while the capability was assembled: the class body had already executed, so this is the"
    " first moment at which the operation's own names exist."
)
"""Appended to every refusal made at assembly, so the reader is not sent back to the class body."""

class _LazyTypes(Mapping[str, Any]):
    """
    A read-only type map that resolves its values the first time it is read.

    The contract types live in modules that import the aspect package — ``ToolsBox`` imports
    ``BaseAction``, which imports ``AspectIntent`` — so importing them here would close a cycle
    at module load. The table is only read when a declaration is checked, which is after every
    module has loaded, so the types are built then and cached.
    """

    def __init__(self, builder: Callable[[], dict[str, Any]]) -> None:
        self._builder = builder
        self._resolved: dict[str, Any] | None = None

    def _types(self) -> dict[str, Any]:
        """Return the resolved map, building it on first use."""
        if self._resolved is None:
            self._resolved = self._builder()
        return self._resolved

    def __getitem__(self, key: str) -> Any:
        return self._types()[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._types())

    def __len__(self) -> int:
        return len(self._types())


def _base_types() -> dict[str, Any]:
    """The types every aspect receives; imported here, not at module load (see ``_LazyTypes``)."""
    from aoa.action_machine.context.context_view import ContextView  # pylint: disable=import-outside-toplevel
    from aoa.action_machine.model.base_params import BaseParams  # pylint: disable=import-outside-toplevel
    from aoa.action_machine.model.base_state import BaseState  # pylint: disable=import-outside-toplevel
    from aoa.action_machine.resources.base_resource import BaseResource  # pylint: disable=import-outside-toplevel
    from aoa.action_machine.runtime.tools_box import ToolsBox  # pylint: disable=import-outside-toplevel

    return {
        "params": BaseParams,
        "state": BaseState,
        "box": ToolsBox,
        "connections": dict[str, BaseResource],
        "ctx": ContextView,
    }


def _compensate_types() -> dict[str, Any]:
    """The compensator's types: two states, because it is called after one was replaced."""
    from aoa.action_machine.context.context_view import ContextView  # pylint: disable=import-outside-toplevel
    from aoa.action_machine.model.base_params import BaseParams  # pylint: disable=import-outside-toplevel
    from aoa.action_machine.model.base_state import BaseState  # pylint: disable=import-outside-toplevel
    from aoa.action_machine.resources.base_resource import BaseResource  # pylint: disable=import-outside-toplevel
    from aoa.action_machine.runtime.tools_box import ToolsBox  # pylint: disable=import-outside-toplevel

    return {
        "params": BaseParams,
        "state_before": BaseState,
        "state_after": BaseState | None,
        "box": ToolsBox,
        "connections": dict[str, BaseResource],
        "error": Exception,
        "ctx": ContextView,
    }


def _on_error_types() -> dict[str, Any]:
    """The handler's types: everything an aspect receives, plus the error that arrived."""
    return {**_base_types(), "error": Exception}


@dataclass(frozen=True)
class AspectContract:
    """
    AI-CORE-BEGIN
    ROLE: One declaration decorator's signature as data: what it receives, when ``ctx`` is added, what each value must be typed as, and what its return must be.
    CONTRACT: ``parameters`` starts with ``self`` and lists the values in the order the pipeline passes them; ``parameters_with_ctx`` is exactly ``parameters`` plus the trailing ``ctx``; ``expected_types`` names only parameters that exist in ``parameters``; ``return_rule`` is one of ``operation_result``, ``state_fragment``, ``none``. The object is frozen, so a contract cannot be altered after it is built.
    INVARIANTS: Every decorator has one entry in ``ASPECT_CONTRACTS`` and no two entries share a ``kind``. A violation of the fields above is a defect of this module, not a fact about a declaration, and is caught by ``test_aspect_contract_table.py`` rather than at run time.
    AI-CORE-END
    """

    kind: str
    parameters: tuple[str, ...]
    parameters_with_ctx: tuple[str, ...]
    expected_types: Mapping[str, Any]
    return_rule: ReturnRule


ASPECT_CONTRACTS: Mapping[str, AspectContract] = MappingProxyType(
    {
        "summary_aspect": AspectContract(
            kind="summary_aspect",
            parameters=_BASE_PARAMETERS,
            parameters_with_ctx=(*_BASE_PARAMETERS, "ctx"),
            expected_types=_LazyTypes(_base_types),
            return_rule="operation_result",
        ),
        "regular_aspect": AspectContract(
            kind="regular_aspect",
            parameters=_BASE_PARAMETERS,
            parameters_with_ctx=(*_BASE_PARAMETERS, "ctx"),
            expected_types=_LazyTypes(_base_types),
            return_rule="state_fragment",
        ),
        "on_error": AspectContract(
            kind="on_error",
            parameters=(*_BASE_PARAMETERS, "error"),
            parameters_with_ctx=(*_BASE_PARAMETERS, "error", "ctx"),
            expected_types=_LazyTypes(_on_error_types),
            return_rule="operation_result",
        ),
        "compensate": AspectContract(
            kind="compensate",
            parameters=_COMPENSATE_PARAMETERS,
            parameters_with_ctx=(*_COMPENSATE_PARAMETERS, "ctx"),
            expected_types=_LazyTypes(_compensate_types),
            return_rule="none",
        ),
    },
)
"""The four declaration contracts, keyed by the decorator's name without the ``@``."""


def _expected_parameters(contract: AspectContract, func: Callable[..., Any]) -> tuple[str, ...]:
    """The names the declaration must use: the ``ctx`` variant only when it can see ``@context_requires``."""
    return contract.parameters_with_ctx if hasattr(func, "_required_context_keys") else contract.parameters


def _context_hint(contract: AspectContract, func: Callable[..., Any], actual: tuple[str, ...]) -> str:
    """Explain the mistake this signature makes most often: where ``@context_requires`` goes.

    The trailing ``ctx`` and the declaration that asks for it are two halves of one thing, and
    the decorator order decides which half the other one sees: ``@context_requires`` must sit
    *under* the declaration, so that the attribute exists by the time this check runs.
    """
    declares_context = hasattr(func, "_required_context_keys")
    takes_ctx = actual[-1] == "ctx" if actual else False
    if takes_ctx and not declares_context:
        return (
            f" This declaration takes ctx but asks for no context: put @context_requires(...) "
            f"under the @{contract.kind} decorator, not above it."
        )
    if declares_context and not takes_ctx:
        return " This declaration asked for context, so it must take the trailing ctx parameter."
    return ""


def validate_positional(contract: AspectContract, func: Callable[..., Any]) -> None:
    """
    Refuse a signature the pipeline cannot call by position, or that hides a value behind a default.

    Raises:
        AspectSignatureError: the signature takes keyword-only parameters, ``*args`` or
            ``**kwargs``, or gives a default to a value the pipeline always supplies.
    """
    passed = ", ".join(contract.parameters)
    signature = inspect.signature(func)
    if func.__code__.co_kwonlyargcount or func.__code__.co_flags & inspect.CO_VARARGS or func.__code__.co_flags & inspect.CO_VARKEYWORDS:
        raise AspectSignatureError(
            f"@{contract.kind}: method '{func.__name__}' must be callable with positional arguments; "
            f"the pipeline passes ({passed}) by position, so keyword-only parameters, *args and "
            f"**kwargs are refused." + _DECLARED_MOMENT
        )
    defaulted = [
        name for name, parameter in signature.parameters.items() if parameter.default is not inspect.Parameter.empty
    ]
    if defaulted:
        raise AspectSignatureError(
            f"@{contract.kind}: method '{func.__name__}' must declare every parameter without a default; "
            f"the pipeline always supplies ({passed}), so ({', '.join(defaulted)}) would never use its "
            f"default and the signature would say something the call does not do." + _DECLARED_MOMENT
        )


def validate_names(contract: AspectContract, func: Callable[..., Any]) -> None:
    """
    Refuse a signature whose parameters are renamed, reordered, or disagree with ``@context_requires``.

    Raises:
        AspectSignatureError: the names, their order or the trailing ``ctx`` differ from the contract.
    """
    expected = _expected_parameters(contract, func)
    actual = tuple(inspect.signature(func).parameters)
    if actual == expected:
        return
    raise AspectSignatureError(
        f"@{contract.kind}: method '{func.__name__}' must declare its parameters as "
        f"({', '.join(expected)}), got ({', '.join(actual)}). The pipeline hands them over in "
        f"that order and Python binds by position, so a renamed or reordered parameter receives "
        f"something other than it says." + _context_hint(contract, func, actual) + _DECLARED_MOMENT
    )





def validate_annotated(contract: AspectContract, func: Callable[..., Any]) -> None:
    """
    Refuse a declaration that leaves a parameter or its return untyped.

    Raises:
        AspectSignatureError: a parameter other than ``self`` carries no annotation, or the
            return does.
    """
    parameters = inspect.signature(func).parameters
    bare = [name for name, parameter in parameters.items() if name != "self" and parameter.annotation is inspect.Parameter.empty]
    if bare:
        raise AspectSignatureError(
            f"@{contract.kind}: method '{func.__name__}' must annotate every parameter it receives; "
            f"({', '.join(bare)}) carry no annotation." + _DECLARED_MOMENT
        )
    if inspect.signature(func).return_annotation is inspect.Signature.empty:
        raise AspectSignatureError(
            f"@{contract.kind}: method '{func.__name__}' must annotate what it returns "
            f"({_return_expectation(contract)})." + _DECLARED_MOMENT
        )


def _return_expectation(contract: AspectContract) -> str:
    """How to describe, in one short phrase, what the return of this kind of declaration must be."""
    if contract.return_rule == "operation_result":
        return "the operation's Result"
    if contract.return_rule == "state_fragment":
        return "dict[str, Any]"
    return "None"


def _resolved_hints(contract: AspectContract, action_cls: type[Any], func: Callable[..., Any]) -> dict[str, Any]:
    """Resolve the annotations, letting the operation's own names and its nested types be found."""
    localns: dict[str, Any] = dict(vars(action_cls))
    localns[action_cls.__name__] = action_cls
    leaf = action_cls.__qualname__.rpartition(".")[2]
    localns[leaf] = action_cls
    try:
        return get_type_hints(func, localns=localns)
    except Exception as exc:  # pylint: disable=broad-except
        raise AspectSignatureError(
            f"@{contract.kind}: {action_cls.__name__}.{func.__name__} annotates its signature with names "
            f"that cannot be resolved ({exc}); the signature is part of the contract, so its annotations "
            f"must be importable." + _ASSEMBLED_MOMENT
        ) from exc


def _name_of(annotation: Any) -> str:
    """A readable name for an annotation in a message."""
    return getattr(annotation, "__name__", None) or str(annotation).replace("typing.", "")


def validate_types(contract: AspectContract, action_cls: type[Any], func: Callable[..., Any]) -> None:
    """
    Refuse a declaration whose annotations resolve to something the pipeline never hands over.

    Called while the graph is assembled, because ``params`` is annotated with the operation's own
    ``Params`` — a name that does not exist while its class body runs.

    Raises:
        AspectSignatureError: an annotation cannot be resolved, names a type the pipeline never
            hands over, or promises a return the pipeline does not read.
    """
    hints = _resolved_hints(contract, action_cls, func)
    for name, expected in contract.expected_types.items():
        actual = hints.get(name)
        if actual is None:
            continue  # a parameter the declaration does not take (ctx, when no context was asked for)
        if name == "connections":
            _validate_connections(contract, action_cls, func, actual)
        elif name == "state_after":
            _validate_state_after(contract, action_cls, func, actual)
        elif name == "error":
            _validate_error(contract, action_cls, func, actual)
        elif not (isinstance(actual, type) and issubclass(actual, expected)):
            raise AspectSignatureError(
                f"@{contract.kind}: {action_cls.__name__}.{func.__name__} annotates '{name}' as "
                f"{_name_of(actual)}, but the pipeline hands over ({', '.join(contract.parameters)}) in "
                f"that order: it must be {_name_of(expected)} or a subclass of it." + _ASSEMBLED_MOMENT
            )
    _validate_return(contract, action_cls, func, hints.get("return"))


def _validate_connections(
    contract: AspectContract,
    action_cls: type[Any],
    func: Callable[..., Any],
    actual: Any,
) -> None:
    """``connections`` is a mapping of connection keys to resources, not a bare mapping."""
    from aoa.action_machine.resources.base_resource import BaseResource  # pylint: disable=import-outside-toplevel

    origin = getattr(actual, "__origin__", None)
    arguments = tuple(getattr(actual, "__args__", ()))
    well_formed = (
        origin is dict
        and len(arguments) == 2
        and isinstance(arguments[0], type)
        and issubclass(arguments[0], str)
        and isinstance(arguments[1], type)
        and issubclass(arguments[1], BaseResource)
    )
    if well_formed:
        return
    raise AspectSignatureError(
        f"@{contract.kind}: {action_cls.__name__}.{func.__name__} annotates 'connections' as "
        f"{_name_of(actual)}, but it must be dict[str, BaseResource]." + _ASSEMBLED_MOMENT
    )


def _validate_state_after(
    contract: AspectContract,
    action_cls: type[Any],
    func: Callable[..., Any],
    actual: Any,
) -> None:
    """The compensator's ``state_after`` is a state or ``None``: the aspect may not have finished."""
    from aoa.action_machine.model.base_state import BaseState  # pylint: disable=import-outside-toplevel

    members = set(getattr(actual, "__args__", ())) or {actual}
    if members == {BaseState, type(None)}:
        return
    raise AspectSignatureError(
        f"@{contract.kind}: {action_cls.__name__}.{func.__name__} annotates 'state_after' as "
        f"{_name_of(actual)}, but the compensator receives BaseState | None — None when the aspect it "
        f"compensates did not finish." + _ASSEMBLED_MOMENT
    )


def _validate_error(
    contract: AspectContract,
    action_cls: type[Any],
    func: Callable[..., Any],
    actual: Any,
) -> None:
    """The handler receives the exception it was declared for, so a specific class is true and a non-exception is not."""
    if isinstance(actual, type) and issubclass(actual, Exception):
        return
    raise AspectSignatureError(
        f"@{contract.kind}: {action_cls.__name__}.{func.__name__} annotates 'error' as "
        f"{_name_of(actual)}, but the handler receives the exception it was declared for: it must be "
        f"Exception or a subclass of it." + _ASSEMBLED_MOMENT
    )


def _validate_return(
    contract: AspectContract,
    action_cls: type[Any],
    func: Callable[..., Any],
    actual: Any,
) -> None:
    """The return is checked against what the pipeline does with it."""
    from aoa.action_machine.intents.action_schema.action_schema_intent_resolver import (  # pylint: disable=import-outside-toplevel
        ActionSchemaIntentResolver,
    )

    if contract.return_rule == "operation_result":
        declared = ActionSchemaIntentResolver.resolve_result_type(action_cls)
        if isinstance(actual, type) and issubclass(declared, actual):
            return
        raise AspectSignatureError(
            f"@{contract.kind}: {action_cls.__name__}.{func.__name__} annotates its return as "
            f"{_name_of(actual)}, but a summary answers with the operation's Result — {declared.__name__}."
            + _ASSEMBLED_MOMENT
        )
    if contract.return_rule == "state_fragment":
        if getattr(actual, "__origin__", None) is dict or actual is dict:
            return
        raise AspectSignatureError(
            f"@{contract.kind}: {action_cls.__name__}.{func.__name__} annotates its return as "
            f"{_name_of(actual)}, but a regular aspect answers with the state fragment dict[str, Any]."
            + _ASSEMBLED_MOMENT
        )
    if actual is None or actual is type(None):
        return
    raise AspectSignatureError(
        f"@{contract.kind}: {action_cls.__name__}.{func.__name__} annotates its return as "
        f"{_name_of(actual)}, but a compensator answers with nothing — its return value is ignored."
        + _ASSEMBLED_MOMENT
    )



__all__ = ["ASPECT_CONTRACTS", "AspectContract", "ReturnRule"]
