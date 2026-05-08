# packages/aoa-action-machine/src/aoa/action_machine/context/runtime_info.py
"""
RuntimeInfo — execution environment metadata container.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``RuntimeInfo`` is a ``Context`` component carrying environment metadata:
hostname, service name/version, container id, and Kubernetes pod name.

It is typically initialized from process/runtime environment and propagated
with every context. Useful for identifying where code runs during scaling,
observability, and incident analysis.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    process environment / deployment metadata
                     |
                     v
    RuntimeInfo(...)
                     |
                     v
    Context(runtime=RuntimeInfo)
                     |
                     +--> logging / tracing / diagnostics
                     +--> ContextView access via @context_requires

    Schema hierarchy:
        BaseSchema(BaseModel)
            └── RuntimeInfo (frozen=True, extra="forbid")

═══════════════════════════════════════════════════════════════════════════════
ASPECT ACCESS MODEL
═══════════════════════════════════════════════════════════════════════════════

Direct RuntimeInfo access from aspect is not provided. Supported path is
``@context_requires`` + ``ContextView``:

    @regular_aspect("Diagnostics")
    @context_requires(Ctx.Runtime.hostname, Ctx.Runtime.service_version)
    async def diagnostics_aspect(self, params, state, box, connections, ctx):
        host = ctx.get(Ctx.Runtime.hostname)              # → "pod-xyz-123"
        version = ctx.get(Ctx.Runtime.service_version)    # → "1.2.3"
        return {}

═══════════════════════════════════════════════════════════════════════════════
DICT-LIKE ACCESS (inherited from BaseSchema)
═══════════════════════════════════════════════════════════════════════════════

    runtime = RuntimeInfo(hostname="pod-xyz-123", service_name="orders-api")

    runtime["hostname"]          # → "pod-xyz-123"
    "service_name" in runtime    # → True
    list(runtime.keys())         # → ["hostname", "service_name", ...]

"""

from pydantic import ConfigDict

from aoa.action_machine.model.base_schema import BaseSchema


class RuntimeInfo(BaseSchema):
    """
AI-CORE-BEGIN
    ROLE: Runtime metadata node in Context.
    CONTRACT: Expose optional deployment/environment fields.
    INVARIANTS: Frozen instance with forbid-extra schema policy.
    AI-CORE-END
"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    hostname: str | None = None
    service_name: str | None = None
    service_version: str | None = None
    container_id: str | None = None
    pod_name: str | None = None
