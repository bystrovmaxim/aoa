# src/action_machine/context/context.py
"""
Context — root action execution context object.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``Context`` aggregates user info (``UserInfo``), request metadata
(``RequestInfo``), and runtime metadata (``RuntimeInfo``).

It is created once per request by authentication coordinator
(``AuthCoordinator`` or ``NoAuthCoordinator``) and passed to machine ``run()``.
Used for role checks, logging, tracing, and controlled data exposure via
``ContextView``.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    Request enters adapter/auth pipeline
                |
                v
    AuthCoordinator.process() -> Context(...)
                |
                v
    ActionProductMachine.run(context, ...)
                |
                +--> RoleChecker (reads context.user.roles)
                +--> logging/tracing (reads request/runtime metadata)
                +--> ContextView for @context_requires methods

    Schema hierarchy:
        BaseSchema(BaseModel)
            └── Context (frozen=True, extra="forbid")
                    ├── user: UserInfo
                    ├── request: RequestInfo
                    └── runtime: RuntimeInfo

═══════════════════════════════════════════════════════════════════════════════
NONE-TO-DEFAULT NORMALIZATION
═══════════════════════════════════════════════════════════════════════════════

Explicit ``None`` in any component is replaced with default instance via
``field_validator``. This guarantees ``ctx.user``, ``ctx.request``, and
``ctx.runtime`` are never ``None``:

    Context(user=None)  →  Context(user=UserInfo())
    Context()           →  Context(user=UserInfo(), request=RequestInfo(), runtime=RuntimeInfo())

This simplifies coordinator code: components may be passed as ``None`` without
risk of validation errors.

═══════════════════════════════════════════════════════════════════════════════
ANONYMOUS CONTEXT
═══════════════════════════════════════════════════════════════════════════════

``Context()`` without args creates anonymous context: empty ``UserInfo``
(``user_id=None``, ``roles=()``), empty ``RequestInfo``, and empty
``RuntimeInfo``. Used by ``NoAuthCoordinator`` for open APIs.

═══════════════════════════════════════════════════════════════════════════════
DOT-PATH NAVIGATION
═══════════════════════════════════════════════════════════════════════════════

Context inherits ``resolve()`` from ``BaseSchema``, enabling nested traversal:

    context.resolve("user.user_id")           → "agent_123"
    context.resolve("user.roles")             → (AdminRole, UserRole)
    context.resolve("request.trace_id")       → "abc-123"
    context.resolve("request.client_ip")      → "192.168.1.1"
    context.resolve("runtime.hostname")       → "pod-xyz-123"
    context.resolve("runtime.service_version") → "1.2.3"

Used by ``ContextView`` for ``@context_requires`` access and by
template/log substitution paths.

In examples below, ``AdminRole`` and ``UserRole`` represent ``BaseRole`` subclasses.

═══════════════════════════════════════════════════════════════════════════════
ASPECT ACCESS MODEL
═══════════════════════════════════════════════════════════════════════════════

Direct Context access from aspect is not supported: ``ToolsBox`` does not store
context. The supported path is ``@context_requires`` + ``ContextView``:

    @regular_aspect("Audit")
    @context_requires(Ctx.User.user_id, Ctx.Request.client_ip)
    async def audit_aspect(self, params, state, box, connections, ctx):
        user_id = ctx.get(Ctx.User.user_id)     # → "agent_123"
        ip = ctx.get(Ctx.Request.client_ip)       # → "192.168.1.1"
        return {}

``ContextView`` delegates to ``context.resolve(key)`` for value lookup.

═══════════════════════════════════════════════════════════════════════════════
DICT-LIKE ACCESS (inherited from BaseSchema)
═══════════════════════════════════════════════════════════════════════════════

    ctx = Context(
        user=UserInfo(user_id="agent_123", roles=(AdminRole,)),
        request=RequestInfo(trace_id="abc-123"),
    )

    ctx["user"]                          # → UserInfo(...)
    ctx["request"]                       # → RequestInfo(...)
    "runtime" in ctx                     # → True
    list(ctx.keys())                     # → ["user", "request", "runtime"]
    ctx.resolve("user.user_id")          # → "agent_123"

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.context.context import Context
    from action_machine.context.user_info import UserInfo
    from action_machine.context.request_info import RequestInfo
    from action_machine.context.runtime_info import RuntimeInfo

    # Full context:
    ctx = Context(
        user=UserInfo(user_id="john_doe", roles=(UserRole, ManagerRole)),
        request=RequestInfo(
            trace_id="abc-123",
            request_path="/api/v1/orders",
            request_method="POST",
            client_ip="192.168.1.1",
        ),
        runtime=RuntimeInfo(
            hostname="pod-xyz-123",
            service_name="orders-api",
            service_version="1.2.3",
        ),
    )

    ctx.resolve("user.user_id")           # → "john_doe"
    ctx.resolve("request.trace_id")       # → "abc-123"
    ctx.resolve("runtime.service_name")   # → "orders-api"

    # Anonymous context:
    anon_ctx = Context()
    anon_ctx.resolve("user.user_id")      # → None
    anon_ctx.resolve("user.roles")        # → []

    # None components are replaced with defaults:
    ctx = Context(user=None, runtime=None)
    ctx.user.user_id                       # -> None (defaulted UserInfo)
    ctx.runtime.hostname                   # -> None (defaulted RuntimeInfo)
"""

from pydantic import ConfigDict, field_validator

from action_machine.context.request_info import RequestInfo
from action_machine.context.runtime_info import RuntimeInfo
from action_machine.context.user_info import UserInfo
from action_machine.model.base_schema import BaseSchema


class Context(BaseSchema):
    """
AI-CORE-BEGIN
    ROLE: Runtime metadata container (user/request/runtime).
    CONTRACT: Expose safe defaults and BaseSchema dot-path resolution.
    INVARIANTS: Frozen object, forbid extra, None inputs normalized to defaults.
    AI-CORE-END
"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    user: UserInfo = UserInfo()
    request: RequestInfo = RequestInfo()
    runtime: RuntimeInfo = RuntimeInfo()

    @field_validator("user", mode="before")
    @classmethod
    def _default_user(cls, v: object) -> object:
        """Replace ``None`` with default ``UserInfo()``."""
        return v if v is not None else UserInfo()

    @field_validator("request", mode="before")
    @classmethod
    def _default_request(cls, v: object) -> object:
        """Replace ``None`` with default ``RequestInfo()``."""
        return v if v is not None else RequestInfo()

    @field_validator("runtime", mode="before")
    @classmethod
    def _default_runtime(cls, v: object) -> object:
        """Replace ``None`` with default ``RuntimeInfo()``."""
        return v if v is not None else RuntimeInfo()
