"""Share a domain without importing either relationship endpoint."""

from aoa.action_machine.domain.base_domain import BaseDomain


class CrossModuleDomain(BaseDomain):
    """Group the independently imported endpoints."""

    name = "cross_module"
    description = "Cross-module inverse resolution"
