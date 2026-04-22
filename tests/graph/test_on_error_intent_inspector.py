# tests/graph/test_on_error_intent_inspector.py
"""Unit tests for OnErrorIntentInspector."""

from __future__ import annotations

from action_machine.context.ctx_constants import Ctx
from action_machine.intents.context.context_requires_decorator import context_requires
from action_machine.intents.on_error.on_error_decorator import on_error
from action_machine.intents.on_error.on_error_intent import OnErrorIntent
from action_machine.legacy.on_error_intent_inspector import (
    OnErrorIntentInspector,
    hydrate_error_handler_row,
)


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
    produced = OnErrorIntentInspector.inspect(_OnErrorAction)
    assert isinstance(produced, list)
    handler_payloads = [p for p in produced if p.node_type == "error_handler"]
    action_payloads = [p for p in produced if p.node_type == "Action"]
    assert len(handler_payloads) == 2
    assert len(action_payloads) == 1
    act = action_payloads[0]
    assert {e.edge_type for e in act.edges} == {"has_error_handler"}
    assert len(act.edges) == 2

    names = {hydrate_error_handler_row(p.node_meta).method_name for p in handler_payloads}
    assert names == {"value_on_error", "typed_on_error"}

    typed_p = next(p for p in handler_payloads if "typed_on_error" in p.node_name)
    typed = hydrate_error_handler_row(typed_p.node_meta)
    assert TypeError in typed.exception_types
    assert RuntimeError in typed.exception_types
    assert typed.description == "With context"
    assert "user.user_id" in typed.context_keys
