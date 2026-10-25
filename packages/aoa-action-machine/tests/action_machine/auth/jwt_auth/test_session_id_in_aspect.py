# tests/auth/jwt_auth/test_session_id_in_aspect.py
"""
Tests: the session id flows from a signed token into an Action aspect.

A token signed with ``sid`` authenticates to a ``UserInfo`` whose ``session_id``
is the claim's exact value; an aspect that declares
``@context_requires(Ctx.User.session_id)`` reads that value through its
``ContextView``. Distinct sessions differ; a refresh within one session carries
the same identifier.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from pydantic import Field

from aoa.action_machine.auth.jwt_auth.jwt_authenticator import JwtAuthenticator
from aoa.action_machine.context import Ctx
from aoa.action_machine.context.context_view import ContextView
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.context_requires.context_requires_decorator import context_requires
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.resources import Connections
from aoa.action_machine.runtime.tools_box import ToolsBox
from aoa.action_machine.testing import TestBench

from ....support.domain_model.roles import AdminRole

_SECRET = "unit-test-secret-key-not-for-production-use"


class SessionDomain(BaseDomain):
    name = "session"
    description = "Session domain."


class EmptyParams(BaseParams):
    pass


class SessionResult(BaseResult):
    session_id: str = Field(description="Session identifier read from context")


@meta(description="Read the declared session id", domain=SessionDomain)
@check_roles(AdminRole)
class SessionAction(BaseAction[EmptyParams, SessionResult]):
    @summary_aspect("Read session")
    @context_requires(Ctx.User.session_id)
    async def session_summary(self, params: EmptyParams, state: BaseState, box: ToolsBox, connections: Connections, ctx: ContextView) -> SessionResult:
        """Return the session identifier the caller declared in ``@context_requires``."""
        return SessionResult(session_id=ctx.get(Ctx.User.session_id))


def _sign(payload: dict[str, Any]) -> str:
    return jwt.encode(payload, _SECRET, algorithm="HS256")


def _make_authenticator() -> JwtAuthenticator:
    return JwtAuthenticator(
        secret_key=_SECRET,
        algorithm="HS256",
        role_registry={"admin": AdminRole},
        session_id_claim="sid",
    )


def _payload(sid: str) -> dict[str, Any]:
    now = datetime.now(UTC)
    return {"sub": "alice", "roles": ["admin"], "sid": sid, "iat": now, "exp": now + timedelta(minutes=30)}


async def test_session_id_flows_from_token_to_aspect() -> None:
    authenticator = _make_authenticator()
    user = await authenticator.authenticate({"token": _sign(_payload("session-A"))})
    assert user is not None
    assert user.session_id == "session-A"

    result = await TestBench(user=user).run(SessionAction(), EmptyParams(), rollup=False)

    assert result.session_id == "session-A"


async def test_distinct_logins_differ_and_refresh_preserves_session() -> None:
    authenticator = _make_authenticator()

    first_login = await authenticator.authenticate({"token": _sign(_payload("session-A"))})
    second_login = await authenticator.authenticate({"token": _sign(_payload("session-B"))})
    refresh = await authenticator.authenticate({"token": _sign(_payload("session-A"))})

    assert first_login is not None and second_login is not None and refresh is not None
    assert first_login.session_id != second_login.session_id
    assert refresh.session_id == first_login.session_id
