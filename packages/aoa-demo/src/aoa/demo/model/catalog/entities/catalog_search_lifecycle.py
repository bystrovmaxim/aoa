# packages/aoa-demo/src/aoa/demo/model/catalog/entities/catalog_search_lifecycle.py
"""Lifecycles for expanded catalog SKU graph demo."""

from pydantic import Field

from aoa.action_machine.domain import (
    BaseStateEntity,
    Lifecycle,
    value,
)


class CatalogSearchStateEntity(BaseStateEntity):
    """Status of the CatalogDense axis."""

    sort_order: int = Field(default=0, description="Presentation order")

    DRAFT = value(code="draft", display_name="Draft", sort_order=1)
    STAGED = value(code="staged", display_name="Staged", sort_order=2)
    ARCHIVED = value(code="archived", display_name="Archived", sort_order=3)



class CatalogSearchLifecycle(Lifecycle[CatalogSearchStateEntity]):
    """draft → staged → archived."""


    _template = (
        Lifecycle().state(CatalogSearchStateEntity.DRAFT).to(CatalogSearchStateEntity.STAGED).initial().state(CatalogSearchStateEntity.STAGED).to(CatalogSearchStateEntity.ARCHIVED).intermediate().state(CatalogSearchStateEntity.ARCHIVED).final()
    )
