# tests/test_fastapi_can_call_parity.py
"""
``.can()`` (the resolver) and ``.call()`` (the real endpoint) share one recipe (chapter 3.5, task 1).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Before ``EndpointExecutionPlan``, ``resolve_verdicts()`` authenticated every
batch item with the adapter's single default ``auth_coordinator`` and never
resolved ``connections`` at all — so a route with its own ``auth_coordinator=``
override, or an ``access_decide`` that reads ``connections``, could answer
"can I?" differently from what a real call to that route would actually
enforce. These tests construct exactly that shape of route and assert the
resolver and the real HTTP call agree — the regression guard for the fix
described in ``EndpointExecutionPlan``'s own module docstring.
"""

from unittest.mock import AsyncMock

from fastapi.testclient import TestClient
from pydantic import Field

from aoa.action_machine.context.context import Context
from aoa.action_machine.context.user_info import UserInfo
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.connection.connection_decorator import connection
from aoa.action_machine.intents.meta.meta_decorator import meta
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.model.base_result import BaseResult
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.fastapi.adapter import FastApiAdapter

from .support import CancelOrderAction, ManagerRole, OrdersDomain, UserRole

# ─────────────────────────────────────────────────────────────────────────────
# auth_coordinator= override: the resolver must use the ROUTE's own
# coordinator for that operation, not the adapter's default.
# ─────────────────────────────────────────────────────────────────────────────


def _user_context() -> Context:
    return Context(user=UserInfo(user_id="u1", roles=(UserRole,)))


def _manager_context() -> Context:
    return Context(user=UserInfo(user_id="m1", roles=(ManagerRole,)))


class TestAuthCoordinatorOverrideParity:
    """A route-level auth_coordinator= override must apply identically to .can() and .call()."""

    def _build_client(self) -> TestClient:
        # Adapter default: resolves a UserRole context — denied for CancelOrderAction
        # (@check_roles(ManagerRole)). The route below overrides with a coordinator
        # that resolves ManagerRole instead — allowed.
        default_auth = AsyncMock()
        default_auth.process.return_value = _user_context()
        override_auth = AsyncMock()
        override_auth.process.return_value = _manager_context()

        machine = ActionProductMachine(loggers=[])
        adapter = FastApiAdapter(machine=machine, auth_coordinator=default_auth)
        adapter.post("/actions/cancel-order", CancelOrderAction, auth_coordinator=override_auth)
        return TestClient(adapter.build())

    def test_real_call_uses_the_route_override_and_succeeds(self) -> None:
        client = self._build_client()

        response = client.post("/actions/cancel-order", json={"order_id": 7})

        assert response.status_code == 200

    def test_resolver_uses_the_same_route_override_not_the_adapter_default(self) -> None:
        """The resolver's entry gate authenticates with the adapter default (UserRole,
        just to get past the 403 gate) — but the per-item check for this operation must
        still use the route's own override (ManagerRole), exactly like the real call."""
        client = self._build_client()

        response = client.post(
            "/permissions/resolve",
            json={"version": 1, "items": [{"operation": "POST /actions/cancel-order", "params": {"order_id": 7}}]},
        )

        assert response.status_code == 200
        result = response.json()["results"][0]
        assert result["kind"] == "success"


# ─────────────────────────────────────────────────────────────────────────────
# connections=: the resolver must resolve and pass the route's own connections
# into access_decide, not a hardcoded None.
# ─────────────────────────────────────────────────────────────────────────────


class _ResourceTestDomain(BaseDomain):
    name = "connection_parity_test"
    description = "Domain for the connections-parity resource fixture."


@meta(description="Marker resource for the connections-parity test", domain=_ResourceTestDomain)
class _FlagResource(BaseResource):
    """Marker resource — access_decide below only succeeds if this is visible."""

    def get_wrapper_class(self):
        return None


class _ConnectionAwareParams(BaseParams):
    pass


class _ConnectionAwareResult(BaseResult):
    status: str = Field(description="Result status")


@meta(description="access_decide reads connections", domain=OrdersDomain)
@check_roles(ManagerRole)
@connection(_FlagResource, key="flag", description="Marker connection for the parity test")
class _ConnectionAwareAction(BaseAction[_ConnectionAwareParams, _ConnectionAwareResult]):
    """Denies unless its registered ``connections`` were actually resolved and passed through."""

    async def access_decide(self, params, context, box, connections) -> bool:
        return connections is not None and "flag" in connections

    @summary_aspect("Run")
    async def run_summary(self, params, state, box, connections):
        return _ConnectionAwareResult(status="ok")


class TestConnectionsParity:
    """A route's registered connections= must reach access_decide identically for .can() and .call()."""

    def _build_client(self) -> TestClient:
        auth = AsyncMock()
        auth.process.return_value = _manager_context()
        machine = ActionProductMachine(loggers=[])
        adapter = FastApiAdapter(machine=machine, auth_coordinator=auth)
        adapter.post("/actions/connection-aware", _ConnectionAwareAction, connections={"flag": _FlagResource()})
        return TestClient(adapter.build())

    def test_real_call_sees_the_registered_connection_and_succeeds(self) -> None:
        client = self._build_client()

        response = client.post("/actions/connection-aware", json={})

        assert response.status_code == 200

    def test_resolver_sees_the_same_registered_connection_not_none(self) -> None:
        """If the resolver still hardcoded connections=None (the pre-EndpointExecutionPlan
        bug), access_decide would see connections=None and deny — diverging from the real call."""
        client = self._build_client()

        response = client.post(
            "/permissions/resolve",
            json={"version": 1, "items": [{"operation": "POST /actions/connection-aware", "params": {}}]},
        )

        assert response.status_code == 200
        result = response.json()["results"][0]
        assert result["kind"] == "success"
