# packages/aoa-maxitor/src/aoa/maxitor/model/core/resources/static_bundle_resource.py
"""
StaticBundleResource — the installed client bundle, read through a resource.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The client's build writes ``build.json`` next to the bundle it produces, with an id of
that build. A tab reports the build it runs; Maxitor compares it with the build it
serves, so a tab left open over a deploy reloads itself (spec 028, FR-090, FR-091),
and the left panel shows the running version (FR-101). Reading that file is reading a
store, so it goes through this resource and nowhere else.

A server started without a built client (the API alone, in development) has no
``build.json``; the build is then empty, and no tab is ever told to reload.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    vite build ──► static/build.json {"build": "<12 hex>"}
                          │
    action aspect ──connections["StaticBundle"].build()──► "<12 hex>" | ""
"""

from __future__ import annotations

import json
from pathlib import Path

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.base_storage import BaseStorage
from aoa.maxitor.model.core.core_domain import CoreDomain

#: Connection key under which actions receive the bundle resource.
STATIC_BUNDLE_CONNECTION_KEY = "StaticBundle"


@meta(description="The installed client bundle and the id of its build", domain=CoreDomain)
class StaticBundleResource(BaseStorage):
    """
    AI-CORE-BEGIN
    ROLE: The resource through which actions learn which client build Maxitor serves.
    CONTRACT: ``build`` returns the ``build`` field of ``build.json`` in the static folder, or ``""``
    when there is no readable file.
    INVARIANTS: Reads only; never writes the bundle.
    AI-CORE-END
    """

    def __init__(self, directory: Path) -> None:
        self._directory = directory

    def get_wrapper_class(self) -> type[BaseStorage] | None:
        """Return ``None``: nested actions read through this same resource."""
        return None

    async def check_rollup_support(self) -> bool:
        """Report that the bundle is not a rollup target."""
        return False

    def build(self) -> str:
        """The id of the client build in the static folder, or ``""`` when there is none."""
        try:
            data = json.loads((self._directory / "build.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return ""
        build = data.get("build") if isinstance(data, dict) else None
        return build if isinstance(build, str) else ""
