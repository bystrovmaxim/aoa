"""
07_extend_context.py — Extend Context (each part)

Context has three parts — `user` (UserInfo), `request` (RequestInfo), `runtime`
(RuntimeInfo). To carry your own call-environment fields (tenant, API version,
deployment region), you EXTEND a part by inheritance with explicit fields, build
it where the Context is born (the auth coordinator), and read it in aspects.

Two facts make this work:

  1. Context fields are typed as the base classes, but pydantic keeps the
     subclass instance as-is (no coercion/stripping) — so a `TenantUserInfo`
     assigned to `Context.user` keeps its `tenant_id`.
  2. Aspects never touch Context directly. They DECLARE the paths they need with
     @context_requires and receive a ContextView. Standard fields have `Ctx.*`
     constants (autocomplete); custom inherited fields use raw string paths.
     A path you did not declare is refused — even if present.

How-to: ../../docs/how-to/authoring-context-extension_draft.md

Run:
    uv run python examples/how_to/07_extend_context.py
"""

import asyncio

from pydantic import Field

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.context import Context, Ctx
from aoa.action_machine.context.request_info import RequestInfo
from aoa.action_machine.context.runtime_info import RuntimeInfo
from aoa.action_machine.context.user_info import UserInfo
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.context_requires.context_requires_decorator import context_requires
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine


# ── Extend each part by inheritance with explicit fields ─────────────────────
class TenantUserInfo(UserInfo):
    tenant_id: str = ""


class VersionedRequestInfo(RequestInfo):
    api_version: str = "v1"


class DeployRuntimeInfo(RuntimeInfo):
    region: str = ""


# ── A normal Action; the aspect declares the custom paths it needs ───────────
class TenancyDomain(BaseDomain):
    name = "tenancy"
    description = "Tenancy domain"


class WhoamiParams(BaseParams):
    pass


class WhoamiResult(BaseResult):
    summary: str = Field(description="Resolved call environment")


@meta(description="Report the call environment", domain=TenancyDomain)
@check_roles(GuestRole)
class WhoamiAction(BaseAction[WhoamiParams, WhoamiResult]):
    # Mix standard Ctx.* constants with raw string paths for the custom fields.
    @summary_aspect("Read environment")
    @context_requires(Ctx.User.user_id, "user.tenant_id", "request.api_version", "runtime.region")
    async def whoami_summary(self, params, state, box, connections, ctx):
        return WhoamiResult(summary=(
            f"user={ctx.get(Ctx.User.user_id)} "
            f"tenant={ctx.get('user.tenant_id')} "
            f"api={ctx.get('request.api_version')} "
            f"region={ctx.get('runtime.region')}"
        ))


async def main() -> None:
    machine = ActionProductMachine()

    # The auth coordinator would build this; here we assemble it directly.
    ctx = Context(
        user=TenantUserInfo(user_id="u-42", tenant_id="acme"),
        request=VersionedRequestInfo(api_version="v3"),
        runtime=DeployRuntimeInfo(region="eu-central"),
    )

    # Proof the subclass survived assignment to the base-typed field:
    print("ctx.user is", type(ctx.user).__name__, "->", ctx.resolve("user.tenant_id"))

    result = await machine.run(ctx, WhoamiAction(), WhoamiParams(), {})
    print(result.summary)


if __name__ == "__main__":
    asyncio.run(main())
