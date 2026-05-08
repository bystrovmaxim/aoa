# packages/aoa-maxitor/src/aoa/maxitor/samples/catalog/entities/catalog_product_lifecycle.py
"""Lifecycle graph for a catalog SKU row (sample)."""

from aoa.action_machine.domain import Lifecycle


class CatalogProductLifecycle(Lifecycle):
    """Three states: draft → active → retired."""

    _template = (
        Lifecycle()
        .state("draft", "Draft").to("active").initial()
        .state("active", "Active").to("retired").intermediate()
        .state("retired", "Retired").final()
    )
