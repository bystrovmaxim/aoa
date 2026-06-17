"""
01_context.py — Assembling Context in tests (with_user / with_request / with_runtime)

The Action reads its environment only through Context, and only the slice it
declared with @context_requires. In a test you assemble that Context with the
TestBench builder — there is no global to set, no object to warm up:

  .with_user(user_id=, roles=(...))    -> UserInfo   (drives @check_roles)
  .with_request(trace_id=, ...)        -> RequestInfo
  .with_runtime(service_name=, ...)    -> RuntimeInfo

The roles you put on the user are what @check_roles actually checks; the fields
you set are what the aspect sees through @context_requires — and only those: a
field the aspect did not declare is refused even when present.

Tutorial: ../../docs/tutorials/step-25-context_draft.md  ·  topic: Context in tests

Run:
    uv run python examples/step_25_context/01_context.py
"""

import asyncio

from pydantic import Field

from aoa.action_machine.auth import ApplicationRole, NoneRole
from aoa.action_machine.context import Ctx
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.exceptions.authorization_error import AuthorizationError
from aoa.action_machine.exceptions.context_access_error import ContextAccessError
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.context_requires.context_requires_decorator import context_requires
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.testing import TestBench


class AuditDomain(BaseDomain):
    name = "audit"
    description = "Audit domain"


class AdminRole(ApplicationRole):
    name = "admin"
    description = "Administrator"


class EmptyParams(BaseParams):
    pass


class WhoamiResult(BaseResult):
    user_id: str = Field(description="Caller id")
    trace_id: str = Field(description="Request trace")
    service_name: str = Field(description="Runtime service")


@meta(description="Echo the declared context", domain=AuditDomain)
@check_roles(AdminRole)
class WhoamiAction(BaseAction[EmptyParams, WhoamiResult]):
    @summary_aspect("Read declared context")
    @context_requires(Ctx.User.user_id, Ctx.Request.trace_id, Ctx.Runtime.service_name)
    async def whoami_summary(self, params, state, box, connections, ctx):
        return WhoamiResult(
            user_id=ctx.get(Ctx.User.user_id),
            trace_id=ctx.get(Ctx.Request.trace_id),
            service_name=ctx.get(Ctx.Runtime.service_name),
        )


class LeakResult(BaseResult):
    user_id: str = Field(description="Declared field")
    client_ip_refused: bool = Field(description="Whether the undeclared field was refused")


@meta(description="Try to read an undeclared context field", domain=AuditDomain)
@check_roles(NoneRole)
class LeakAction(BaseAction[EmptyParams, LeakResult]):
    @summary_aspect("Read only what was declared")
    @context_requires(Ctx.User.user_id)          # client_ip is NOT declared
    async def leak_summary(self, params, state, box, connections, ctx):
        try:
            ctx.get(Ctx.Request.client_ip)        # present in context, but undeclared
            refused = False
        except ContextAccessError:
            refused = True
        return LeakResult(user_id=ctx.get(Ctx.User.user_id), client_ip_refused=refused)


async def main() -> None:
    # 1. Assemble the whole Context; the aspect reads exactly its declared slice.
    bench = (
        TestBench()
        .with_user(user_id="u-test", roles=(AdminRole,))
        .with_request(trace_id="t-1")
        .with_runtime(service_name="orders-svc")
    )
    r = await bench.run(WhoamiAction(), EmptyParams(), rollup=False)
    print(f"1) with_user/request/runtime -> user_id={r.user_id} trace_id={r.trace_id} service={r.service_name}")

    # 2. The roles on the user are what @check_roles checks — drop them and it fails.
    try:
        await TestBench().run(WhoamiAction(), EmptyParams(), rollup=False)   # default user: no admin
    except AuthorizationError as exc:
        print(f"2) no admin role             -> AuthorizationError: {exc}")

    # 3. A field present in the Context but NOT declared is refused.
    leak_bench = TestBench().with_request(client_ip="10.0.0.7")   # client_ip IS set...
    r = await leak_bench.run(LeakAction(), EmptyParams(), rollup=False)
    print(f"3) undeclared field          -> client_ip refused: {r.client_ip_refused}  (it was set, but not declared)")


if __name__ == "__main__":
    asyncio.run(main())
