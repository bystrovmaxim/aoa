# packages/aoa-demo/src/aoa/demo/model/catalog/entities/catalog_dense_lifecycle.py
"""Lifecycles for expanded catalog SKU graph demo."""

from aoa.action_machine.domain import Lifecycle


class CatalogDenseLifecycle(Lifecycle):
    """draft → staged → archived."""

    _template = (
        Lifecycle()
        .state("draft", "Draft")
        .to("staged")
        .initial()
        .state("staged", "Staged")
        .to("archived")
        .intermediate()
        .state("archived", "Archived")
        .final()
    )
