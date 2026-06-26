# packages/aoa-demo/src/aoa/demo/model/catalog/domain.py
"""Bounded-context marker for catalog and pricing."""

from aoa.action_machine.domain import BaseDomain


class CatalogDomain(BaseDomain):
    name = "catalog"
    description = "Product catalog and merchandising slice for the sample app"
