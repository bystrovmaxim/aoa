# packages/aoa-action-machine/src/aoa/action_machine/intents/aspects/regular_aspect_decorator.py
"""
Decorator ``@regular_aspect`` declares a regular pipeline step.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Marks an action method as a regular aspect. The method must return a ``dict``
containing the complete next state.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

The decorator writes ``_new_aspect_meta`` on the method. The inspector reads
that metadata into aspect snapshot entries. At runtime, the machine executes
regular aspects in declaration order and replaces state with the returned dict.

If ``@context_requires`` is present, ``ContextView`` is passed as ``ctx``:
- without context: ``(self, params, state, box, connections)``
- with context: ``(self, params, state, box, connections, ctx)``

    @regular_aspect(...)
           |
           v
    declaration invariants
           |
           v
    _new_aspect_meta on method
           |
           v
    inspector snapshot
           |
           v
    runtime state replacement

"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from aoa.action_machine.exceptions.async_required_error import AsyncRequiredError
from aoa.action_machine.exceptions.decorator_target_error import DecoratorTargetError
from aoa.action_machine.exceptions.description_contract_error import DescriptionContractError
from aoa.action_machine.exceptions.description_type_error import DescriptionTypeError
from aoa.action_machine.exceptions.naming_suffix_error import NamingSuffixError
from aoa.action_machine.intents.aspects.aspect_signature import ASPECT_CONTRACTS, validate_names, validate_positional

# Required method suffix for regular aspect declarations.
_REQUIRED_SUFFIX = "_aspect"


def _description_type_invariant(description: Any) -> None:
    if not isinstance(description, str):
        raise DescriptionTypeError(f"@regular_aspect expects a string description, " f"got {type(description).__name__}.")


def _description_non_empty_invariant(description: str) -> None:
    if not description.strip():
        raise DescriptionContractError(
            "@regular_aspect: description cannot be empty or whitespace. " "Provide a non-empty step description."
        )


def _method_callable_invariant(func: Any) -> None:
    if not callable(func):
        raise DecoratorTargetError(
            f"@regular_aspect can only be applied to methods. " f"Got object of type {type(func).__name__}: {func!r}."
        )


def _method_async_invariant(func: Any, description: str) -> None:
    if not asyncio.iscoroutinefunction(func):
        raise AsyncRequiredError(
            f'@regular_aspect("{description}"): method {func.__name__} '
            f"must be async (async def). "
            f"Synchronous methods are not supported."
        )


def _signature_invariant(func: Any) -> None:
    """Refuse a signature the pipeline cannot call: position first, then the names, then ``ctx``."""
    contract = ASPECT_CONTRACTS["regular_aspect"]
    validate_positional(contract, func)
    validate_names(contract, func)


def _method_suffix_invariant(func: Any, description: str) -> None:
    if not func.__name__.endswith(_REQUIRED_SUFFIX):
        raise NamingSuffixError(
            f"@regular_aspect(\"{description}\"): method '{func.__name__}' "
            f"must end with '{_REQUIRED_SUFFIX}'. "
            f"Rename to '{func.__name__}{_REQUIRED_SUFFIX}' "
            f"or another name with the '{_REQUIRED_SUFFIX}' suffix."
        )


def regular_aspect(description: str) -> Callable[[Any], Any]:
    """
    Mark an action method as a regular pipeline step.
    """
    _description_type_invariant(description)
    _description_non_empty_invariant(description)

    def decorator(func: Any) -> Any:
        """Validate target method and attach regular-aspect metadata."""
        _method_callable_invariant(func)
        _method_async_invariant(func, description)
        _signature_invariant(func)
        _method_suffix_invariant(func, description)
        func._new_aspect_meta = {
            "type": "regular",
            "description": description,
        }
        return func

    return decorator
