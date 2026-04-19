# src/action_machine/testing/stubs.py
"""
Context stubs for ActionMachine testing.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The module provides ready-to-use stubs with sensible defaults for all execution
context components: user (``UserInfo``), request info (``RequestInfo``),
runtime info (``RuntimeInfo``), and aggregated context (``Context``).

Stubs remove the need to manually build context objects in each test. A typical
test starts with one line:

    ctx = ContextStub()

Every stub supports field overrides via named arguments:

    ctx = ContextStub(user=UserInfoStub(user_id="admin", roles=(AdminRole,)))

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

[UserInfoStub]     [RequestInfoStub]     [RuntimeInfoStub]
      |                   |                     |
      +-------------------+----------+----------+
                                 |
                             ContextStub
                                 |
                              Context

COMPONENTS:
- ``UserInfoStub`` - user context factory. Defaults:
  ``user_id="test_user"``, ``roles=(StubTesterRole,)``.
- ``RuntimeInfoStub`` - runtime context factory. Defaults:
  ``hostname="test-host"``, ``service_name="test-service"``,
  ``service_version="0.0.1"``.
- ``RequestInfoStub`` - request context factory. Defaults:
  ``trace_id="test-trace-000"``, ``request_path="/test"``,
  ``protocol="test"``, ``request_method="TEST"``.
- ``ContextStub`` - full context factory composing the three stubs above.

INVARIANTS:
- Factories return real domain types, not mocks.
- Defaults are valid for typical role/context validation.
- Stubs expose only explicitly declared fields of underlying models.

EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.testing import (
        ContextStub,
        UserInfoStub,
        RequestInfoStub,
        RuntimeInfoStub,
    )

    # Minimal test setup:
    result = await machine.run(
        context=ContextStub(),
        action=PingAction(),
        params=PingAction.Params(),
        rollup=False,
    )

    # Test with specific user:
    admin_ctx = ContextStub(
        user=UserInfoStub(user_id="admin_1", roles=(AdminRole, ManagerRole)),
    )

    # Test with specific trace_id:
    traced_ctx = ContextStub(
        request=RequestInfoStub(trace_id="trace-abc-123"),
    )

    # Individual stubs:
    user = UserInfoStub(roles=(AdminRole,))
    runtime = RuntimeInfoStub(hostname="prod-server-01")
    request = RequestInfoStub(request_path="/api/v1/orders", protocol="https")

    # Extension via UserInfo subclass:
    class TenantUserInfo(UserInfo):
        tenant_id: str = "default"

    tenant_user = TenantUserInfo(
        user_id="admin",
        roles=(AdminRole,),
        tenant_id="acme",
    )
    ctx = ContextStub(user=tenant_user)

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Stubs do not bypass validation of underlying pydantic/domain models.
- Invalid override values still raise model-level validation errors.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE
═══════════════════════════════════════════════════════════════════════════════

Use these factories to build deterministic test contexts quickly while keeping
runtime behavior close to production object shapes.
"""

from action_machine.auth.application_role import ApplicationRole
from action_machine.auth.base_role import BaseRole
from action_machine.intents.role_mode.role_mode_decorator import RoleMode, role_mode
from action_machine.context.context import Context
from action_machine.context.request_info import RequestInfo
from action_machine.context.runtime_info import RuntimeInfo
from action_machine.context.user_info import UserInfo


@role_mode(RoleMode.ALIVE)
class StubTesterRole(ApplicationRole):
    """Default assignable role for ``UserInfoStub`` and TestBench user defaults."""

    name = "tester"
    description = "Default role for UserInfoStub in tests."


def UserInfoStub(
    user_id: str = "test_user",
    roles: tuple[type[BaseRole], ...] | list[type[BaseRole]] | None = None,
) -> UserInfo:
    """
    Create ``UserInfo`` stub with sensible defaults.
    """
    resolved: tuple[type[BaseRole], ...] = (
        (StubTesterRole,) if roles is None else tuple(roles)
    )
    return UserInfo(user_id=user_id, roles=resolved)


def RuntimeInfoStub(
    hostname: str = "test-host",
    service_name: str = "test-service",
    service_version: str = "0.0.1",
    container_id: str | None = None,
    pod_name: str | None = None,
) -> RuntimeInfo:
    """
    Create ``RuntimeInfo`` stub with sensible defaults.
    """
    return RuntimeInfo(
        hostname=hostname,
        service_name=service_name,
        service_version=service_version,
        container_id=container_id,
        pod_name=pod_name,
    )


def RequestInfoStub(
    trace_id: str = "test-trace-000",
    request_path: str = "/test",
    protocol: str = "test",
    request_method: str = "TEST",
    full_url: str | None = None,
    client_ip: str | None = None,
    user_agent: str | None = None,
    request_timestamp: None = None,
) -> RequestInfo:
    """
    Create ``RequestInfo`` stub with sensible defaults.
    """
    return RequestInfo(
        trace_id=trace_id,
        request_path=request_path,
        protocol=protocol,
        request_method=request_method,
        full_url=full_url,
        client_ip=client_ip,
        user_agent=user_agent,
        request_timestamp=request_timestamp,
    )


def ContextStub(
    user: UserInfo | None = None,
    request: RequestInfo | None = None,
    runtime: RuntimeInfo | None = None,
) -> Context:
    """
    Create full ``Context`` stub by composing user/request/runtime stubs.
    """
    return Context(
        user=user if user is not None else UserInfoStub(),
        request=request if request is not None else RequestInfoStub(),
        runtime=runtime if runtime is not None else RuntimeInfoStub(),
    )
