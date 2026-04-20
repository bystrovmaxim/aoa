# src/action_machine/context/ctx_constants.py
"""
Context path constants for ``@context_requires`` decorator.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The module provides nested ``Ctx`` constants describing all standard execution
context fields (``Context``). Every constant is a dot-path string used by
``@context_requires`` and consumed through ``ContextView.get()``.

Constants are aligned with real fields from ``UserInfo``, ``RequestInfo``,
and ``RuntimeInfo``.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    Ctx.User      -> UserInfo fields (user_id, roles)
    Ctx.Request   -> RequestInfo fields (trace_id, request_timestamp, request_path,
                    request_method, full_url, client_ip, protocol, user_agent)
    Ctx.Runtime   -> RuntimeInfo fields (hostname, service_name, service_version,
                    container_id, pod_name)

Every constant is a ``"component.field"`` string, for example:
    Ctx.User.user_id    == "user.user_id"
    Ctx.Request.trace_id == "request.trace_id"
    Ctx.Runtime.hostname == "runtime.hostname"

The path matches ``Context.resolve()`` navigation:
    context.resolve("user.user_id")      → context.user.user_id
    context.resolve("request.trace_id")  → context.request.trace_id

═══════════════════════════════════════════════════════════════════════════════
EXTENDING CONTEXT COMPONENTS
═══════════════════════════════════════════════════════════════════════════════

``UserInfo``, ``RequestInfo``, and ``RuntimeInfo`` can be extended by
inheritance with explicit fields. ``Ctx`` constants cover standard fields with
IDE autocomplete. For custom inherited fields, use raw string paths:

    class BillingUserInfo(UserInfo):
        billing_plan: str = "free"

    @context_requires(Ctx.User.user_id, "user.billing_plan")
    async def billing_aspect(self, params, state, box, connections, ctx):
        plan = ctx.get("user.billing_plan")
        ...

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.context import Ctx
    from action_machine.intents.context import context_requires

    @regular_aspect("Permission check")
    @context_requires(Ctx.User.user_id, Ctx.User.roles)
    async def check_permissions_aspect(self, params, state, box, connections, ctx):
        user_id = ctx.get(Ctx.User.user_id)
        roles = ctx.get(Ctx.User.roles)
        ...

    # Mix of constants and string paths for custom fields:
    @regular_aspect("Billing")
    @context_requires(Ctx.User.user_id, "user.billing_plan")
    async def billing_aspect(self, params, state, box, connections, ctx):
        plan = ctx.get("user.billing_plan")
        ...

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Typed constant namespace for context field declarations.
CONTRACT: Provide stable dot-path literals for @context_requires usage.
INVARIANTS: String-only constants grouped by User/Request/Runtime components.
FLOW: Ctx constant -> @context_requires -> ContextView.get() -> Context.resolve().
FAILURES: Unknown/custom fields require explicit string paths.
EXTENSION POINTS: Add new constants when standard context schema expands.
AI-CORE-END
"""


class _UserFields:
    """
    Dot-path constants for ``UserInfo`` fields inside ``Context``.
    """

    user_id: str = "user.user_id"
    """User identifier. ``UserInfo`` type: ``str | None``."""

    roles: str = "user.roles"
    """Assigned role classes. ``UserInfo`` type: role tuple."""


class _RequestFields:
    """
    Dot-path constants for ``RequestInfo`` fields inside ``Context``.
    """

    trace_id: str = "request.trace_id"
    """Request trace identifier. ``RequestInfo`` type: ``str | None``."""

    request_timestamp: str = "request.request_timestamp"
    """Request timestamp. ``RequestInfo`` type: ``datetime | None``."""

    request_path: str = "request.request_path"
    """Endpoint path or tool name. ``RequestInfo`` type: ``str | None``."""

    request_method: str = "request.request_method"
    """HTTP method or ``"tool_call"``. ``RequestInfo`` type: ``str | None``."""

    full_url: str = "request.full_url"
    """Full request URL. ``RequestInfo`` type: ``str | None``."""

    client_ip: str = "request.client_ip"
    """Client IP address. ``RequestInfo`` type: ``str | None``."""

    protocol: str = "request.protocol"
    """Transport protocol (``"http"``, ``"https"``, ``"mcp"``)."""

    user_agent: str = "request.user_agent"
    """User-Agent header. ``RequestInfo`` type: ``str | None``."""


class _RuntimeFields:
    """
    Dot-path constants for ``RuntimeInfo`` fields inside ``Context``.
    """

    hostname: str = "runtime.hostname"
    """Host or container name. ``RuntimeInfo`` type: ``str | None``."""

    service_name: str = "runtime.service_name"
    """Service name. ``RuntimeInfo`` type: ``str | None``."""

    service_version: str = "runtime.service_version"
    """Service version. ``RuntimeInfo`` type: ``str | None``."""

    container_id: str = "runtime.container_id"
    """Docker container ID. ``RuntimeInfo`` type: ``str | None``."""

    pod_name: str = "runtime.pod_name"
    """Kubernetes pod name. ``RuntimeInfo`` type: ``str | None``."""


class Ctx:
    """
    Nested constant namespace for declaring context field access.

    Three groups correspond to Context components:
        Ctx.User    -> UserInfo
        Ctx.Request -> RequestInfo
        Ctx.Runtime -> RuntimeInfo

    Each constant is a string dot-path. IDE autocomplete and static typing
    reduce typo risk in declarations.

    Example:
        @context_requires(Ctx.User.user_id, Ctx.Request.trace_id)
        async def my_aspect(self, params, state, box, connections, ctx):
            user_id = ctx.get(Ctx.User.user_id)
            trace = ctx.get(Ctx.Request.trace_id)
    """

    User = _UserFields
    """UserInfo field paths."""

    Request = _RequestFields
    """RequestInfo field paths."""

    Runtime = _RuntimeFields
    """RuntimeInfo field paths."""
