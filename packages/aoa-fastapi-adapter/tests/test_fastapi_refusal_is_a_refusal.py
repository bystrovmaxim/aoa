# packages/aoa-fastapi-adapter/tests/test_fastapi_refusal_is_a_refusal.py
"""
A refusal reaches an HTTP caller as a refusal, not as an unhandled failure (FR-004).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

An access decision ends one of three ways, and the transport has to keep them apart: a
refusal is the answer 403 with the decision in its body, and a gate that could not
complete is not a refusal at all. Neither may arrive as an unhandled error.

The calls below run a **real** machine — no mocked ``run`` — so the transport is measured
against the engine's own behaviour. That is the point: the exception the engine raises for
a refusal is the engine's business, and this file pins the contract the caller sees.
``raise_server_exceptions=False`` is deliberate: with it a leaked exception shows up as a
500 the test can see, instead of as a traceback the test would swallow.

═══════════════════════════════════════════════════════════════════════════════
STRUCTURE
═══════════════════════════════════════════════════════════════════════════════

TestARefusalStaysARefusal — 403 with the gate named, on both paths a caller can be refused
TestAFailureIsNotARefusal — a gate that could not complete is never answered as 403
TestAnAllowedCall          — the guard against a vacuous test: the same route answers 200
"""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from aoa.action_machine.auth.application_role import ApplicationRole
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
from aoa.fastapi.adapter import FastApiAdapter

from .support import TestDomain

_FAILURE_TEXT = "postgres://primary:5432 refused the connection"


class OrdersAdminRole(ApplicationRole):
    """The role the probe route lists, and the caller below does not hold."""

    pass


@meta(description="refusals: an operation only an orders admin may call", domain=TestDomain)
@check_roles(OrdersAdminRole)
class RefusingAction(BaseAction["RefusingAction.Params", "RefusingAction.Result"]):
    """An operation whose object check refuses a caller who holds the role."""

    class Params(BaseParams):
        """No inputs."""

    class Result(BaseResult):
        """The answer an allowed call would produce."""

        message: str = ""

    @access_decide("Refuse the object this caller may not touch")
    async def refusing_access_decide(
        self,
        params: RefusingAction.Params,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> Verdict:
        """Refuse: the caller holds the role, the object is not theirs."""
        return FORBIDDEN_OBJECT

    @summary_aspect("Answer")
    async def refusing_summary(
        self,
        params: RefusingAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> RefusingAction.Result:
        """Produce the result an allowed caller would see."""
        return RefusingAction.Result(message="allowed")


@meta(description="refusals: an operation whose gate cannot complete", domain=TestDomain)
@check_roles(OrdersAdminRole)
class FailingGateAction(BaseAction["FailingGateAction.Params", "FailingGateAction.Result"]):
    """An operation whose object check cannot complete at all."""

    class Params(BaseParams):
        """No inputs."""

    class Result(BaseResult):
        """No outputs."""

        message: str = ""

    @access_decide("Fail, as a store that is down fails")
    async def failing_access_decide(
        self,
        params: FailingGateAction.Params,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> Verdict:
        """Fail, the way a store that is down fails."""
        raise ConnectionError(_FAILURE_TEXT)

    @summary_aspect("Answer")
    async def failing_summary(
        self,
        params: FailingGateAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> FailingGateAction.Result:
        """Produce the result a healthy call would see."""
        return FailingGateAction.Result(message="allowed")


@meta(description="refusals: an operation everyone with the role may call", domain=TestDomain)
@check_roles(OrdersAdminRole)
class AllowingAction(BaseAction["AllowingAction.Params", "AllowingAction.Result"]):
    """An operation with no object check at all."""

    class Params(BaseParams):
        """No inputs."""

    class Result(BaseResult):
        """No outputs."""

        message: str = ""

    @summary_aspect("Answer")
    async def allowing_summary(
        self,
        params: AllowingAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> AllowingAction.Result:
        """Produce the result."""
        return AllowingAction.Result(message="allowed")


def _caller(roles: tuple[type[ApplicationRole], ...]) -> Context:
    """A caller holding exactly the given roles."""
    return Context(user=UserInfo(user_id="u-1", roles=roles))


class _FixedAuth:
    """An auth coordinator that answers with one caller — the transport's identity step."""

    def __init__(self, context: Context) -> None:
        self._context = context

    async def process(self, request: Any) -> Context:
        """Return the caller this coordinator was built with."""
        return self._context


def _client(action: type[BaseAction[Any, Any]], caller: Context) -> TestClient:
    """An app with one route for ``action``, answering for ``caller``."""
    machine = ActionProductMachine(loggers=[], cache_coordinator=None)
    adapter = FastApiAdapter(machine=machine, auth_coordinator=_FixedAuth(caller))
    adapter.post("/guarded", action)
    return TestClient(adapter.build(), raise_server_exceptions=False)


class TestARefusalStaysARefusal:
    def test_a_caller_without_the_role_is_refused(self) -> None:
        """403, and not an unhandled failure, when the roles step refuses."""
        client = _client(RefusingAction, _caller(()))

        response = client.post("/guarded", json={})

        assert response.status_code == 403

    def test_the_body_names_the_gate_that_refused(self) -> None:
        client = _client(RefusingAction, _caller(()))

        response = client.post("/guarded", json={})

        assert response.json() == {"detail": "Access denied by CHECK_ROLES."}

    def test_a_caller_with_the_role_is_refused_by_the_object_check(self) -> None:
        """The same route, a caller the role step admits: still a refusal, still 403."""
        client = _client(RefusingAction, _caller((OrdersAdminRole,)))

        response = client.post("/guarded", json={})

        assert response.status_code == 403
        assert "ACCESS_DECIDE" in response.json()["detail"]

    def test_no_refusal_arrives_as_a_server_error(self) -> None:
        for caller in (_caller(()), _caller((OrdersAdminRole,))):
            client = _client(RefusingAction, caller)

            response = client.post("/guarded", json={})

            assert response.status_code < 500

    def test_the_refusal_carries_no_framework_prose_of_its_own(self) -> None:
        """What the body says beyond the gate word is nothing this test can predict."""
        client = _client(RefusingAction, _caller(()))

        detail = client.post("/guarded", json={}).json()["detail"]

        assert detail.startswith("Access denied by CHECK_ROLES.")


class TestAFailureIsNotARefusal:
    def test_a_gate_that_cannot_complete_is_not_a_refusal(self) -> None:
        """A caller the role step admits, whose gate is down, is not told "no"."""
        client = _client(FailingGateAction, _caller((OrdersAdminRole,)))

        response = client.post("/guarded", json={})

        assert response.status_code != 403

    def test_the_failure_text_stays_out_of_the_body(self) -> None:
        client = _client(FailingGateAction, _caller((OrdersAdminRole,)))

        response = client.post("/guarded", json={})

        assert _FAILURE_TEXT not in response.text


class TestAnAllowedCall:
    def test_an_allowed_call_answers_with_the_result(self) -> None:
        """The guard against a vacuous test: this route does answer 200 when nothing refuses."""
        client = _client(AllowingAction, _caller((OrdersAdminRole,)))

        response = client.post("/guarded", json={})

        assert response.status_code == 200
        assert response.json()["message"] == "allowed"
