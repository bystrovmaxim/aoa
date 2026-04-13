# tests/intents/context/test_context_requires_intent_validators.py
"""ContextRequiresIntent marker when any pipeline method requests context keys."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from action_machine.intents.context.context_requires_intent import (
    ContextRequiresIntent,
    require_context_requires_intent_marker,
)


def test_require_context_requires_raises_when_keys_present_without_mixin() -> None:
    class Plain:
        pass

    aspect = SimpleNamespace(method_name="a", context_keys=frozenset({"user.id"}))
    with pytest.raises(TypeError, match="ContextRequiresIntent"):
        require_context_requires_intent_marker(Plain, [aspect], [], [])


def test_require_context_requires_checks_error_handlers_and_compensators() -> None:
    class Plain:
        pass

    handler = SimpleNamespace(method_name="h", context_keys=frozenset({"x"}))
    with pytest.raises(TypeError, match="h"):
        require_context_requires_intent_marker(Plain, [], [handler], [])

    comp = SimpleNamespace(method_name="c", context_keys=frozenset({"y"}))
    with pytest.raises(TypeError, match="c"):
        require_context_requires_intent_marker(Plain, [], [], [comp])


def test_require_context_requires_noop_without_keys() -> None:
    class Plain:
        pass

    require_context_requires_intent_marker(
        Plain,
        [SimpleNamespace(method_name="a", context_keys=frozenset())],
        [],
        [],
    )


def test_require_context_requires_noop_when_mixin_present() -> None:
    class Host(ContextRequiresIntent):
        pass

    aspect = SimpleNamespace(method_name="a", context_keys=frozenset({"k"}))
    require_context_requires_intent_marker(Host, [aspect], [], [])
