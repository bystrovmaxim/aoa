# packages/aoa-action-machine/src/aoa/action_machine/context/request_info.py
"""
RequestInfo — inbound request metadata container.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``RequestInfo`` is a ``Context`` component containing inbound request metadata:
trace identifiers, path, method, client IP, protocol, and transport-specific
details (HTTP, MCP, etc.).

It is populated at ingress (typically by ``ContextAssembler``) and propagated
through runtime for logging, tracing, performance analysis, and audit use cases.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    transport request
          |
          v
    ContextAssembler -> RequestInfo(...)
          |
          v
    Context(request=RequestInfo)
          |
          +--> logging / tracing
          +--> ContextView for @context_requires access

    Schema hierarchy:
        BaseSchema(BaseModel)
            └── RequestInfo (frozen=True, extra="forbid")

═══════════════════════════════════════════════════════════════════════════════
ASPECT ACCESS MODEL
═══════════════════════════════════════════════════════════════════════════════

Direct RequestInfo access from aspects is not provided. Supported path is
``@context_requires`` + ``ContextView``:

    @regular_aspect("Request logging")
    @context_requires(Ctx.Request.trace_id, Ctx.Request.client_ip)
    async def log_request_aspect(self, params, state, box, connections, ctx):
        trace = ctx.get(Ctx.Request.trace_id)     # → "abc-123"
        ip = ctx.get(Ctx.Request.client_ip)        # → "192.168.1.1"
        return {}

═══════════════════════════════════════════════════════════════════════════════
DICT-LIKE ACCESS (inherited from BaseSchema)
═══════════════════════════════════════════════════════════════════════════════

    req = RequestInfo(trace_id="abc-123", client_ip="192.168.1.1")

    req["trace_id"]         # → "abc-123"
    "client_ip" in req      # → True
    list(req.keys())        # → ["trace_id", "request_timestamp", ...]

"""

from datetime import datetime

from pydantic import ConfigDict

from aoa.action_machine.model.base_schema import BaseSchema


class RequestInfo(BaseSchema):
    """
AI-CORE-BEGIN
    ROLE: Request metadata node in Context.
    CONTRACT: Expose typed optional fields for transport-level request details.
    INVARIANTS: Frozen instance with forbid-extra schema policy.
    AI-CORE-END
"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    trace_id: str | None = None
    request_timestamp: datetime | None = None
    request_path: str | None = None
    request_method: str | None = None
    full_url: str | None = None
    client_ip: str | None = None
    protocol: str | None = None
    user_agent: str | None = None
