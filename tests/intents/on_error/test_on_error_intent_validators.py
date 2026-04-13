# tests/intents/on_error/test_on_error_intent_validators.py
"""OnErrorIntent marker and overlapping handler validation."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from action_machine.intents.on_error.on_error_intent import (
    require_on_error_intent_marker,
    validate_error_handlers,
)


@dataclass(frozen=True)
class _ErrorHandlerSnap:
    """Same fields as OnErrorIntentInspector.Snapshot.ErrorHandler (duck-typed for tests)."""

    method_name: str
    exception_types: tuple[type[Exception], ...]
    description: str = "d"
    method_ref: object = None
    context_keys: frozenset[str] = frozenset()


def _handler(name: str, *exc_types: type[Exception]) -> _ErrorHandlerSnap:
    return _ErrorHandlerSnap(method_name=name, exception_types=exc_types)


def test_require_on_error_intent_marker_raises_without_mixin() -> None:
    class Plain:
        pass

    handlers = [_handler("h1", ValueError)]
    with pytest.raises(TypeError, match="OnErrorIntent"):
        require_on_error_intent_marker(Plain, handlers)  # type: ignore[arg-type]


def test_validate_error_handlers_noop_for_single_handler() -> None:
    class Host:
        __name__ = "Host"

    validate_error_handlers(Host, [_handler("h", ValueError)])  # type: ignore[arg-type]


def test_validate_error_handlers_detects_unreachable_subclass() -> None:
    class Host:
        __name__ = "Host"

    handlers = [
        _handler("broad", Exception),
        _handler("narrow", ValueError),
    ]
    with pytest.raises(TypeError, match="narrow"):
        validate_error_handlers(Host, handlers)  # type: ignore[arg-type]
