# packages/aoa-mcp-adapter/tests/test_mcp_refusal_is_a_refusal.py
"""
A refusal reaches an MCP caller as a refusal, not as an unhandled failure (FR-004).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

An MCP tool call answers in an envelope, and a refusal has its own code in it:
``PERMISSION_DENIED``. A gate that could not complete is a different answer with a
different code, and neither may escape the handler as an exception.

The calls below run a **real** machine — no mocked ``run`` — so the transport is measured
against the engine's own behaviour. The exception the engine raises for a refusal is the
engine's business; this file pins the envelope a caller receives.

═══════════════════════════════════════════════════════════════════════════════
STRUCTURE
═══════════════════════════════════════════════════════════════════════════════

TestARefusalStaysARefusal — PERMISSION_DENIED, on both paths a caller can be refused
TestAFailureIsNotARefusal — a gate that could not complete is never a permission error
TestAnAllowedCall          — the guard against a vacuous test: the same tool answers OK
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from aoa.action_machine.context.context import Context
from aoa.action_machine.context.user_info import UserInfo
from aoa.action_machine.intents.access_control import FORBIDDEN_OBJECT, Verdict
from aoa.action_machine.intents.access_decide import access_decide
from aoa.action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta.meta_decorator import meta
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.model.base_result import BaseResult
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.action_machine.runtime.tools_box import ToolsBox
from aoa.mcp.adapter import _make_tool_handler
from aoa.mcp.route_record import McpRouteRecord

from .support import AdminRole, TestDomain

_FAILURE_TEXT = "postgres://primary:5432 refused the connection"


@meta(description="refusals: a tool whose object check refuses", domain=TestDomain)
@check_roles(AdminRole)
class RefusingToolAction(BaseAction["RefusingToolAction.Params", "RefusingToolAction.Result"]):
    """A tool whose object check refuses a caller who holds the role."""

    class Params(BaseParams):
        """No inputs."""

    class Result(BaseResult):
        """The answer an allowed call would produce."""

        message: str = ""

    @access_decide("Refuse the object this caller may not touch")
    async def refusing_access_decide(
        self,
        params: RefusingToolAction.Params,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> Verdict:
        """Refuse: the caller holds the role, the object is not theirs."""
        return FORBIDDEN_OBJECT

    @summary_aspect("Answer")
    async def refusing_summary(
        self,
        params: RefusingToolAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> RefusingToolAction.Result:
        """Produce the result an allowed caller would see."""
        return RefusingToolAction.Result(message="allowed")


@meta(description="refusals: a tool whose gate cannot complete", domain=TestDomain)
@check_roles(AdminRole)
class FailingGateToolAction(BaseAction["FailingGateToolAction.Params", "FailingGateToolAction.Result"]):
    """A tool whose object check cannot complete at all."""

    class Params(BaseParams):
        """No inputs."""

    class Result(BaseResult):
        """No outputs."""

        message: str = ""

    @access_decide("Fail, as a store that is down fails")
    async def failing_gate_access_decide(
        self,
        params: FailingGateToolAction.Params,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> Verdict:
        """Fail, the way a store that is down fails."""
        raise ConnectionError(_FAILURE_TEXT)

    @summary_aspect("Answer")
    async def failing_gate_summary(
        self,
        params: FailingGateToolAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> FailingGateToolAction.Result:
        """Produce the result a healthy call would see."""
        return FailingGateToolAction.Result(message="allowed")


@meta(description="refusals: a tool everyone with the role may call", domain=TestDomain)
@check_roles(AdminRole)
class AllowingToolAction(BaseAction["AllowingToolAction.Params", "AllowingToolAction.Result"]):
    """A tool with no object check at all."""

    class Params(BaseParams):
        """No inputs."""

    class Result(BaseResult):
        """No outputs."""

        message: str = ""

    @summary_aspect("Answer")
    async def allowing_summary(
        self,
        params: AllowingToolAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> AllowingToolAction.Result:
        """Produce the result."""
        return AllowingToolAction.Result(message="allowed")


class _FixedAuth:
    """An auth coordinator that answers with one caller — the transport's identity step."""

    def __init__(self, context: Context) -> None:
        self._context = context

    async def process(self, request: Any) -> Context:
        """Return the caller this coordinator was built with."""
        return self._context


def _envelope(text: str) -> dict[str, Any]:
    """Parse the JSON envelope one tool result carries."""
    return json.loads(text)


def _caller(roles: tuple[type[AdminRole], ...]) -> Context:
    """A caller holding exactly the given roles."""
    return Context(user=UserInfo(user_id="u-1", roles=roles))


async def _call(action: type[BaseAction[Any, Any]], caller: Context) -> Any:
    """Invoke one tool through its handler, with a real machine behind it."""
    machine = ActionProductMachine(loggers=[], cache_coordinator=None)
    record = McpRouteRecord(action_class=action, tool_name="refusals.tool")
    handler = _make_tool_handler(record, machine, _FixedAuth(caller), machine.graph_coordinator)

    return await handler()


class TestARefusalStaysARefusal:
    async def test_a_caller_without_the_role_is_refused(self) -> None:
        result = await _call(RefusingToolAction, _caller(()))

        assert result.isError is True
        assert _envelope(result.content[0].text)["code"] == "PERMISSION_DENIED"

    async def test_the_message_names_the_gate_that_refused(self) -> None:
        result = await _call(RefusingToolAction, _caller(()))

        assert _envelope(result.content[0].text)["message"] == "Access denied by CHECK_ROLES."

    async def test_a_caller_with_the_role_is_refused_by_the_object_check(self) -> None:
        result = await _call(RefusingToolAction, _caller((AdminRole,)))

        assert result.isError is True
        assert _envelope(result.content[0].text)["code"] == "PERMISSION_DENIED"
        assert "ACCESS_DECIDE" in _envelope(result.content[0].text)["message"]

    async def test_no_refusal_is_an_internal_error(self) -> None:
        for caller in (_caller(()), _caller((AdminRole,))):
            result = await _call(RefusingToolAction, caller)

            assert _envelope(result.content[0].text)["code"] != "INTERNAL_ERROR"


class TestAFailureIsNotARefusal:
    async def test_a_gate_that_cannot_complete_is_not_a_permission_error(self) -> None:
        result = await _call(FailingGateToolAction, _caller((AdminRole,)))

        assert _envelope(result.content[0].text)["code"] != "PERMISSION_DENIED"

    async def test_it_is_still_reported_as_a_failure(self) -> None:
        result = await _call(FailingGateToolAction, _caller((AdminRole,)))

        assert result.isError is True

    async def test_the_failure_text_stays_out_of_the_envelope(self) -> None:
        result = await _call(FailingGateToolAction, _caller((AdminRole,)))

        assert _FAILURE_TEXT not in result.content[0].text


class TestAnAllowedCall:
    async def test_an_allowed_call_answers_ok(self) -> None:
        """The guard against a vacuous test: this tool does answer OK when nothing refuses."""
        result = await _call(AllowingToolAction, _caller((AdminRole,)))

        assert result.isError is False
        assert _envelope(result.content[0].text)["code"] == "OK"


@pytest.mark.parametrize("roles", [(), (AdminRole,)])
async def test_the_handler_never_raises(roles: tuple[type[AdminRole], ...]) -> None:
    """Whatever the decision, the handler answers — nothing escapes it."""
    for action in (RefusingToolAction, FailingGateToolAction, AllowingToolAction):
        result = await _call(action, _caller(roles))

        assert result.content
