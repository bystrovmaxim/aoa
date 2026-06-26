# packages/aoa-demo/src/aoa/demo/model/build.py
"""Sample module list for import-time registration side effects.

Mirror of :data:`aoa.maxitor.interchange_demo_coordinator.SAMPLE_MODEL_REGISTRATION_MODULE_NAMES`
(keep both in sync).
"""

from __future__ import annotations

from typing import Final

_MODULES: Final[tuple[str, ...]] = (
    "aoa.demo.model.roles",
    # billing: full contour, matching store depth
    "aoa.demo.model.billing.domain",
    "aoa.demo.model.billing.entities",
    "aoa.demo.model.billing.dependencies",
    "aoa.demo.model.billing.resources",
    "aoa.demo.model.billing.plugins",
    "aoa.demo.model.billing.actions",
    # messaging
    "aoa.demo.model.messaging.domain",
    "aoa.demo.model.messaging.entities",
    "aoa.demo.model.messaging.dependencies",
    "aoa.demo.model.messaging",
    "aoa.demo.model.messaging.resources",
    "aoa.demo.model.messaging.plugins",
    "aoa.demo.model.messaging.actions",
    # catalog
    "aoa.demo.model.catalog.domain",
    "aoa.demo.model.catalog.entities",
    "aoa.demo.model.catalog.dependencies",
    "aoa.demo.model.catalog.resources",
    "aoa.demo.model.catalog.plugins",
    # synthetic domains for heterogeneous ERD / graph cardinality demos
    "aoa.demo.model.identity.domain",
    "aoa.demo.model.identity.entities",
    "aoa.demo.model.inventory.domain",
    "aoa.demo.model.inventory.entities",
    "aoa.demo.model.analytics.domain",
    "aoa.demo.model.analytics.entities",
    # ERD topology echoes: clinical intake/dispatch mesh + QA portfolio mesh
    "aoa.demo.model.clinical_supply.domain",
    "aoa.demo.model.clinical_supply.entities",
    "aoa.demo.model.assurance_portfolio.domain",
    "aoa.demo.model.assurance_portfolio.entities",
    # store (depends on billing/messaging services)
    "aoa.demo.model.store.marketplace_operations_domain",
    "aoa.demo.model.store.store_domain",
    "aoa.demo.model.store.dependencies",
    "aoa.demo.model.store.entities",
    "aoa.demo.model.store.resources",
    "aoa.demo.model.store.plugins",
    "aoa.demo.model.catalog.actions",
    "aoa.demo.model.store.actions",
    # entity wire projection demo (PR-5)
    "aoa.demo.model.entity_projection_demo.domain",
    "aoa.demo.model.entity_projection_demo.entities",
    "aoa.demo.model.entity_projection_demo.actions",
    # support: @depends on BaseAction in the same domain and in store
    "aoa.demo.model.support.support_domain",
    "aoa.demo.model.support.entities",
    "aoa.demo.model.support.actions",
    # operational slices mirroring heavyweight use-case cardinality (diagram harnesses)
    "aoa.demo.model.catalog_custody.catalog_custody_domain",
    "aoa.demo.model.catalog_custody.entities",
    "aoa.demo.model.catalog_custody.actions",
    "aoa.demo.model.settlement_desks.settlement_desks_domain",
    "aoa.demo.model.settlement_desks.entities",
    "aoa.demo.model.settlement_desks.actions",
    "aoa.demo.model.telemetry_pipeline.telemetry_pipeline_domain",
    "aoa.demo.model.telemetry_pipeline.entities",
    "aoa.demo.model.telemetry_pipeline.actions",
    "aoa.demo.model.logistics_mesh.logistics_mesh_domain",
    "aoa.demo.model.logistics_mesh.entities",
    "aoa.demo.model.logistics_mesh.actions",
)
