# packages/aoa-demo/src/aoa/demo/fastapi_mcp_services/system_domain.py
"""SystemDomain — cross-cutting utilities (e.g. ping)."""

from aoa.action_machine.domain import BaseDomain


class SystemDomain(BaseDomain):
    """System-level utilities (e.g. liveness ping)."""

    name = "system"
    description = "Cross-cutting system utilities."
