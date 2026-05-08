# packages/aoa-maxitor/src/aoa/maxitor/samples/build.py
"""Sample module list for import-time registration side effects."""

from __future__ import annotations

from typing import Final

_MODULES: Final[tuple[str, ...]] = (
    "aoa.maxitor.samples.roles",
    # billing: full contour, matching store depth
    "aoa.maxitor.samples.billing.domain",
    "aoa.maxitor.samples.billing.entities",
    "aoa.maxitor.samples.billing.dependencies",
    "aoa.maxitor.samples.billing.resources",
    "aoa.maxitor.samples.billing.plugins",
    "aoa.maxitor.samples.billing.actions",
    # messaging
    "aoa.maxitor.samples.messaging.domain",
    "aoa.maxitor.samples.messaging.entities",
    "aoa.maxitor.samples.messaging.dependencies",
    "aoa.maxitor.samples.messaging",
    "aoa.maxitor.samples.messaging.resources",
    "aoa.maxitor.samples.messaging.plugins",
    "aoa.maxitor.samples.messaging.actions",
    # catalog
    "aoa.maxitor.samples.catalog.domain",
    "aoa.maxitor.samples.catalog.entities",
    "aoa.maxitor.samples.catalog.dependencies",
    "aoa.maxitor.samples.catalog.resources",
    "aoa.maxitor.samples.catalog.plugins",
    # synthetic domains for heterogeneous ERD / graph cardinality demos
    "aoa.maxitor.samples.identity.domain",
    "aoa.maxitor.samples.identity.entities",
    "aoa.maxitor.samples.inventory.domain",
    "aoa.maxitor.samples.inventory.entities",
    "aoa.maxitor.samples.analytics.domain",
    "aoa.maxitor.samples.analytics.entities",
    # ERD topology echoes: clinical intake/dispatch mesh + QA portfolio mesh
    "aoa.maxitor.samples.clinical_supply.domain",
    "aoa.maxitor.samples.clinical_supply.entities",
    "aoa.maxitor.samples.assurance_portfolio.domain",
    "aoa.maxitor.samples.assurance_portfolio.entities",
    # store (depends on billing/messaging services)
    "aoa.maxitor.samples.store.domain",
    "aoa.maxitor.samples.store.dependencies",
    "aoa.maxitor.samples.store.entities",
    "aoa.maxitor.samples.store.resources",
    "aoa.maxitor.samples.store.plugins",
    "aoa.maxitor.samples.catalog.actions",
    "aoa.maxitor.samples.store.actions",
    # support: @depends on BaseAction in the same domain and in store
    "aoa.maxitor.samples.support.domain",
    "aoa.maxitor.samples.support.entities",
    "aoa.maxitor.samples.support.actions",
)
