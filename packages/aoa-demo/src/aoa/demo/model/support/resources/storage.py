# packages/aoa-demo/src/aoa/demo/model/support/resources/storage.py
"""SupportStorage — the store that holds the support domain's entities."""

from __future__ import annotations

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.base_storage import BaseStorage
from aoa.demo.model.support.support_domain import SupportDomain


@meta(description="Stores the support model (stub)", domain=SupportDomain)
class SupportStorage(BaseStorage):
    """Hold the support domain's entities; the demo never opens it."""
