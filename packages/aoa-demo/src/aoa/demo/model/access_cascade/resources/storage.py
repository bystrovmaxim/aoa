# packages/aoa-demo/src/aoa/demo/model/access_cascade/resources/storage.py
"""AccessCascadeStorage — the store that holds the access cascade domain's entities."""

from __future__ import annotations

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources import BaseResource, BaseStorage
from aoa.demo.model.access_cascade.access_cascade_domain import AccessCascadeDomain
from aoa.demo.model.data_sources.access_cascade_data_source import AccessCascadeDataSource


@meta(description="Stores the access cascade model (stub)", domain=AccessCascadeDomain)
class AccessCascadeStorage(BaseStorage[AccessCascadeDataSource]):
    """Hold the access cascade domain's entities; the demo never opens it."""

    def get_wrapper_class(self) -> type[BaseResource] | None:
        """No wrapper: a nested action may use this resource as it is."""
        return None
