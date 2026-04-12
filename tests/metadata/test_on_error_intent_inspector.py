# tests/metadata/test_on_error_intent_inspector.py
"""Unit tests for OnErrorIntentInspector."""

from __future__ import annotations

from action_machine.context.context_requires_decorator import context_requires
from action_machine.context.ctx_constants import Ctx
from action_machine.on_error.on_error_decorator import on_error
from action_machine.on_error.on_error_intent import OnErrorIntent
from action_machine.on_error.on_error_intent_inspector import OnErrorIntentInspector


class _NoOnErrorAction(OnErrorIntent):
    pass


class _OnErrorAction(OnErrorIntent):
    @on_error(ValueError, description="Value error handler")
    async def value_on_error(self, params, state, box, connections, error):
        return {"status": "ok"}

    @on_error((TypeError, RuntimeError), description="With context")
    @context_requires(Ctx.User.user_id)
    async def typed_on_error(self, params, state, box, connections, error, ctx):
        return {"status": "ctx", "ctx": bool(ctx)}


def test_on_error_inspector_returns_none_without_handlers() -> None:
    assert OnErrorIntentInspector.inspect(_NoOnErrorAction) is None


def test_on_error_inspector_builds_payload_with_handlers() -> None:
    payload = OnErrorIntentInspector.inspect(_OnErrorAction)
    assert payload is not None
    assert payload.node_type == "error_handler"

    data = dict(payload.node_meta)
    handlers = data["error_handlers"]
    assert len(handlers) == 2

    names = {entry[0] for entry in handlers}
    assert "value_on_error" in names
    assert "typed_on_error" in names

    typed = next(entry for entry in handlers if entry[0] == "typed_on_error")
    assert TypeError in typed[1]
    assert RuntimeError in typed[1]
    assert typed[2] == "With context"
    assert "user.user_id" in typed[4]
