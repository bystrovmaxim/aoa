# packages/aoa-examples/src/aoa/examples/model/build.py
"""Sample module list for import-time registration side effects.

Mirror of :data:`aoa.maxitor.interchange_demo_coordinator.SAMPLE_MODEL_REGISTRATION_MODULE_NAMES`
(keep both in sync).
"""

from __future__ import annotations

from typing import Final

_MODULES: Final[tuple[str, ...]] = (
    "aoa.examples.model.roles",
    # billing: full contour, matching store depth
    "aoa.examples.model.billing.domain",
    "aoa.examples.model.billing.entities",
    "aoa.examples.model.billing.dependencies",
    "aoa.examples.model.billing.resources",
    "aoa.examples.model.billing.plugins",
    "aoa.examples.model.billing.actions",
    # messaging
    "aoa.examples.model.messaging.domain",
    "aoa.examples.model.messaging.entities",
    "aoa.examples.model.messaging.dependencies",
    "aoa.examples.model.messaging",
    "aoa.examples.model.messaging.resources",
    "aoa.examples.model.messaging.plugins",
    "aoa.examples.model.messaging.actions",
    # catalog
    "aoa.examples.model.catalog.domain",
    "aoa.examples.model.catalog.entities",
    "aoa.examples.model.catalog.dependencies",
    "aoa.examples.model.catalog.resources",
    "aoa.examples.model.catalog.plugins",
    # synthetic domains for heterogeneous ERD / graph cardinality demos
    "aoa.examples.model.identity.domain",
    "aoa.examples.model.identity.entities",
    "aoa.examples.model.inventory.domain",
    "aoa.examples.model.inventory.entities",
    "aoa.examples.model.analytics.domain",
    "aoa.examples.model.analytics.entities",
    # ERD topology echoes: clinical intake/dispatch mesh + QA portfolio mesh
    "aoa.examples.model.clinical_supply.domain",
    "aoa.examples.model.clinical_supply.entities",
    "aoa.examples.model.assurance_portfolio.domain",
    "aoa.examples.model.assurance_portfolio.entities",
    # store (depends on billing/messaging services)
    "aoa.examples.model.store.marketplace_operations_domain",
    "aoa.examples.model.store.store_domain",
    "aoa.examples.model.store.dependencies",
    "aoa.examples.model.store.entities",
    "aoa.examples.model.store.resources",
    "aoa.examples.model.store.plugins",
    "aoa.examples.model.catalog.actions",
    "aoa.examples.model.store.actions",
    # entity wire projection demo (PR-5)
    "aoa.examples.model.entity_projection_demo.domain",
    "aoa.examples.model.entity_projection_demo.entities",
    "aoa.examples.model.entity_projection_demo.actions",
    # support: @depends on BaseAction in the same domain and in store
    "aoa.examples.model.support.support_domain",
    "aoa.examples.model.support.entities",
    "aoa.examples.model.support.actions",
    # operational slices mirroring heavyweight use-case cardinality (diagram harnesses)
    "aoa.examples.model.catalog_custody.catalog_custody_domain",
    "aoa.examples.model.catalog_custody.entities",
    "aoa.examples.model.catalog_custody.actions",
    "aoa.examples.model.settlement_desks.settlement_desks_domain",
    "aoa.examples.model.settlement_desks.entities",
    "aoa.examples.model.settlement_desks.actions",
    "aoa.examples.model.telemetry_pipeline.telemetry_pipeline_domain",
    "aoa.examples.model.telemetry_pipeline.entities",
    "aoa.examples.model.telemetry_pipeline.actions",
    "aoa.examples.model.logistics_mesh.logistics_mesh_domain",
    "aoa.examples.model.logistics_mesh.entities",
    "aoa.examples.model.logistics_mesh.actions",
)
