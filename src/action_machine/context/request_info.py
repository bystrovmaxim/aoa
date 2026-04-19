# src/action_machine/context/request_info.py
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
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Immutable after construction.
- Extra fields are forbidden (``extra="forbid"``).
- Extension is explicit via inheritance with declared fields:

    class ExtendedRequestInfo(RequestInfo):
        correlation_id: str | None = None
        ab_variant: str | None = None

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

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    from datetime import datetime

    req = RequestInfo(
        trace_id="abc-123",
        request_timestamp=datetime.utcnow(),
        request_path="/api/v1/orders",
        request_method="POST",
        client_ip="192.168.1.1",
        protocol="https",
    )

    req["trace_id"]                  # → "abc-123"
    req.resolve("request_method")    # → "POST"
    req.model_dump()                 # → {"trace_id": "abc-123", ...}

    # Extension via inheritance:
    class TracedRequestInfo(RequestInfo):
        correlation_id: str | None = None
        ab_variant: str | None = None

    req = TracedRequestInfo(
        trace_id="abc-123",
        correlation_id="corr-456",
        ab_variant="control",
    )

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- This model does not validate protocol semantics (for example, method/path
  combinations); it stores metadata as provided.
- Access restrictions for aspects are enforced by ``ContextView``, not here.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Immutable request-metadata schema inside execution context.
CONTRACT: Carry transport request metadata with strict schema boundaries.
INVARIANTS: Frozen object, forbid extra fields, optional typed attributes.
FLOW: ingress assembly -> context propagation -> logging/tracing/context view reads.
FAILURES: Validation errors occur only for schema/type violations.
EXTENSION POINTS: Inherit RequestInfo for project-specific request attributes.
AI-CORE-END
"""

from datetime import datetime

from pydantic import ConfigDict

from action_machine.model.base_schema import BaseSchema


class RequestInfo(BaseSchema):
    """
    Immutable schema with request metadata fields.

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
