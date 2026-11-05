"""Share a domain without importing either relationship endpoint."""

from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.base_storage import BaseStorage


class CrossModuleDomain(BaseDomain):
    """Group the independently imported endpoints."""

    name = "cross_module"
    description = "Cross-module inverse resolution"


@meta(description="Stores the crossmodule entities", domain=CrossModuleDomain)
class CrossModuleStorage(BaseStorage):
    """Hold the entities of CrossModuleDomain."""
