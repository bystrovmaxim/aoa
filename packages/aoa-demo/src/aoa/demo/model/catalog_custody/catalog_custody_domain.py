# packages/aoa-demo/src/aoa/demo/model/catalog_custody/catalog_custody_domain.py
"""CatalogCustodyDomain — regulated SKU catalog with custody and lineage controls."""

from __future__ import annotations

from aoa.action_machine.domain import BaseDomain


class CatalogCustodyDomain(BaseDomain):
    """Custody tiering, regulated attributes, and auditor-facing reconciliation flows."""

    name = "catalog_custody"
    description = "Regulated product catalog: custody tiers, lineage attestations, posting reconciliations"
