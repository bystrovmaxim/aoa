# packages/aoa-action-machine/tests/support/complete_relationships/domain.py
"""The shared domain for the two-module reciprocal relationship fixtures."""

from aoa.action_machine.domain import BaseDomain
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.base_storage import BaseStorage


class CrossDomain(BaseDomain):
    """Domain both declaration modules belong to."""

    name = "cross"
    description = "Cross-module"


@meta(description="Stores the cross entities")
class CrossStorage(BaseStorage):
    """Hold the entities of CrossDomain."""
