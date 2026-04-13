# tests/intents/on_error/test_on_error_intent_validators.py
"""OnErrorIntent marker and overlapping handler validation."""

from __future__ import annotations

import pytest

from action_machine.graph.inspectors.on_error_intent_inspector import OnErrorIntentInspector
from action_machine.intents.on_error.on_error_intent import (
    require_on_error_intent_marker,
    validate_error_handlers,
)


def _handler(
    name: str,
    *exc_types: type[Exception],
) -> OnErrorIntentInspector.Snapshot.ErrorHandler:
    return OnErrorIntentInspector.Snapshot.ErrorHandler(
        method_name=name,
        exception_types=exc_types,
        description="d",
        method_ref=None,
        context_keys=frozenset(),
    )


def test_require_on_error_intent_marker_raises_without_mixin() -> None:
    class Plain:
        pass

    handlers = [_handler("h1", ValueError)]
    with pytest.raises(TypeError, match="OnErrorIntent"):
        require_on_error_intent_marker(Plain, handlers)


def test_validate_error_handlers_noop_for_single_handler() -> None:
    class Host:
        __name__ = "Host"

    validate_error_handlers(Host, [_handler("h", ValueError)])


def test_validate_error_handlers_detects_unreachable_subclass() -> None:
    class Host:
        __name__ = "Host"

    handlers = [
        _handler("broad", Exception),
        _handler("narrow", ValueError),
    ]
    with pytest.raises(TypeError, match="narrow"):
        validate_error_handlers(Host, handlers)
