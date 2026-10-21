# packages/aoa-demo/src/aoa/demo/model/catalog/entities/catalog_dense_lifecycle.py
"""Lifecycles for expanded catalog SKU graph demo."""

from pydantic import Field

from aoa.action_machine.domain import (
    BaseStateEntity,
    Lifecycle,
    StateVocabulary,
)


class CatalogDenseStateEntity(BaseStateEntity):
    """Status of the CatalogDense axis."""

    sort_order: int = Field(default=0, description="Presentation order")


class CatalogDenseLifecycle(Lifecycle, StateVocabulary):
    """draft → staged → archived."""

    DRAFT = CatalogDenseStateEntity(code="draft", display_name="Draft", sort_order=1)
    STAGED = CatalogDenseStateEntity(code="staged", display_name="Staged", sort_order=2)
    ARCHIVED = CatalogDenseStateEntity(code="archived", display_name="Archived", sort_order=3)

    _template = (
        Lifecycle().state(DRAFT).to(STAGED).initial().state(STAGED).to(ARCHIVED).intermediate().state(ARCHIVED).final()
    )
