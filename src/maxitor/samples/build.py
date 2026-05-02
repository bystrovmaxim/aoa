# src/maxitor/samples/build.py
"""Sample module list for import-time registration side effects."""

from __future__ import annotations

from typing import Final

_MODULES: Final[tuple[str, ...]] = (
    "maxitor.samples.roles",
    # billing: full contour, matching store depth
    "maxitor.samples.billing.domain",
    "maxitor.samples.billing.entities",
    "maxitor.samples.billing.dependencies",
    "maxitor.samples.billing.resources",
    "maxitor.samples.billing.plugins",
    "maxitor.samples.billing.actions",
    # messaging
    "maxitor.samples.messaging.domain",
    "maxitor.samples.messaging.entities",
    "maxitor.samples.messaging.dependencies",
    "maxitor.samples.messaging",
    "maxitor.samples.messaging.resources",
    "maxitor.samples.messaging.plugins",
    "maxitor.samples.messaging.actions",
    # catalog
    "maxitor.samples.catalog.domain",
    "maxitor.samples.catalog.entities",
    "maxitor.samples.catalog.dependencies",
    "maxitor.samples.catalog.resources",
    "maxitor.samples.catalog.plugins",
    # store (depends on billing/messaging services)
    "maxitor.samples.store.domain",
    "maxitor.samples.store.dependencies",
    "maxitor.samples.store.entities",
    "maxitor.samples.store.resources",
    "maxitor.samples.store.plugins",
    "maxitor.samples.catalog.actions",
    "maxitor.samples.store.actions",
    # support: @depends on BaseAction in the same domain and in store
    "maxitor.samples.support.domain",
    "maxitor.samples.support.actions",
)
