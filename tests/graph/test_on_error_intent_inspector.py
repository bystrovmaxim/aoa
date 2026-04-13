# tests/graph/test_on_error_intent_inspector.py
"""Unit tests for OnErrorIntentInspector."""

from __future__ import annotations

from action_machine.graph.inspectors.on_error_intent_inspector import OnErrorIntentInspector
from action_machine.intents.context.context_requires_decorator import context_requires
from action_machine.intents.context.ctx_constants import Ctx
from action_machine.intents.on_error.on_error_decorator import on_error
from action_machine.intents.on_error.on_error_intent import OnErrorIntent


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

    names = {dict(entry)["method_name"] for entry in handlers}
    assert "value_on_error" in names
    assert "typed_on_error" in names

    typed = next(e for e in handlers if dict(e)["method_name"] == "typed_on_error")
    td = dict(typed)
    assert TypeError in td["exception_types"]
    assert RuntimeError in td["exception_types"]
    assert td["description"] == "With context"
    assert "user.user_id" in td["context_keys"]
