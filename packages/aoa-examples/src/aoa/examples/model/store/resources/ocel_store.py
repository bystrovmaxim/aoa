# packages/aoa-examples/src/aoa/examples/model/store/resources/ocel_store.py
"""Store OCEL store resource for ``@connection`` wiring."""

from __future__ import annotations

from pathlib import Path

from aoa.action_machine.intents.meta import meta
from aoa.examples.model.store.store_domain import StoreDomain
from aoa.ocel import InMemoryOcelStoreResource


@meta(description="In-memory OCEL 2.0 export target for storefront traces", domain=StoreDomain)
class StoreOcelStoreResource(InMemoryOcelStoreResource):
    """Writes ``*.ocel.json`` on ``close()``; root action owns ``open`` / ``close``."""

    def __init__(self, output_file: Path) -> None:
        super().__init__(output_file=output_file)
