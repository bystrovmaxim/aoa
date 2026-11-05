# packages/aoa-demo/src/aoa/demo/model/access_cascade/resources/storage.py
"""AccessCascadeStorage — the store that holds the access cascade domain's entities."""

from __future__ import annotations

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.base_storage import BaseStorage
from aoa.demo.model.access_cascade.access_cascade_domain import AccessCascadeDomain


@meta(description="Stores the access cascade model (stub)", domain=AccessCascadeDomain)
class AccessCascadeStorage(BaseStorage):
    """Hold the access cascade domain's entities; the demo never opens it."""
