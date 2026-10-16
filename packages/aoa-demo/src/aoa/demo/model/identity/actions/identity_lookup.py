# packages/aoa-demo/src/aoa/demo/model/identity/actions/identity_lookup.py
"""
IdentityLookupAction — read a person and record the login in one transaction.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The action declares the store it needs with ``@connection(…, key="identity")`` and
never learns how it was supplied — a connection from the application's pool, or an
in-memory stand-in. What it does learn is the shape of the store's two operations:
a read by identifier, and a write that owns its own transaction.

The declaration is per call, so the route that registers this action hands over a
``PerCallConnection``: the store is created for this call, and the boundary closes
it afterwards — which returns the connection to the pool.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    POST /api/v1/identity/lookup   |   MCP tool "identity.lookup"
              |
              v
    @connection(IdentityStoreBase, key="identity")
              |
              v
    connections["identity"].read_person(person_id)      -> rows, or none
    connections["identity"].record_login(person_id, at) -> BEGIN / INSERT / COMMIT
              |
              v
    Result(person_id, found, email, display_name, login_recorded)

"""

from __future__ import annotations

from typing import cast

from pydantic import Field

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.connection import connection  # pylint: disable=no-name-in-module
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult, BaseState
from aoa.action_machine.resources import BaseResource
from aoa.action_machine.runtime.tools_box import ToolsBox

from ..domain import IdentityDomain
from ..resources.identity_store_base import IdentityStoreBase


@meta(description="Read an identity person and record the login", domain=IdentityDomain)
@check_roles(GuestRole)
@connection(IdentityStoreBase, key="identity", description="Identity store, one connection per call")
class IdentityLookupAction(BaseAction["IdentityLookupAction.Params", "IdentityLookupAction.Result"]):

    class Params(BaseParams):
        """Identity lookup input parameters."""

        person_id: str = Field(
            description="Identifier of the person to read",
            min_length=1,
            examples=["person-1"],
        )
        at: str = Field(
            description="Moment the login is recorded at, ISO 8601",
            min_length=1,
            examples=["2026-10-16T12:00:00Z"],
        )

    class Result(BaseResult):
        """Identity lookup result payload."""

        person_id: str = Field(description="Identifier that was looked up", examples=["person-1"])
        found: bool = Field(description="Whether the store answered with a person")
        email: str | None = Field(default=None, description="Person's e-mail, when found")
        display_name: str | None = Field(default=None, description="Person's display name, when found")
        login_recorded: bool = Field(default=False, description="Whether the login was committed")

    @summary_aspect("Read the person and record the login")
    async def identity_summary(
        self,
        params: IdentityLookupAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> IdentityLookupAction.Result:
        """Read through the declared connection, and write inside the transaction it owns."""
        store = cast(IdentityStoreBase, connections["identity"])

        rows = await store.read_person(params.person_id)
        if not rows:
            return IdentityLookupAction.Result(person_id=params.person_id, found=False)

        await store.record_login(params.person_id, params.at)

        person = rows[0]
        return IdentityLookupAction.Result(
            person_id=params.person_id,
            found=True,
            email=person.get("email"),
            display_name=person.get("display_name"),
            login_recorded=True,
        )
