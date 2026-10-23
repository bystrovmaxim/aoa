# packages/aoa-demo/src/aoa/demo/model/catalog/entities/catalog_dense_lifecycle.py
# pylint: disable=undefined-variable  # the class-name alias is the declaration surface
"""Lifecycles for expanded catalog SKU graph demo."""

from pydantic import Field

from aoa.action_machine.domain import (
    BaseStateEntity,
    Lifecycle,
    value,
)


class CatalogDenseStateEntity(BaseStateEntity):
    """Status of the CatalogDense axis."""

    sort_order: int = Field(default=0, description="Presentation order")

    DRAFT = value(code="draft", display_name="Draft", sort_order=1)
    STAGED = value(code="staged", display_name="Staged", sort_order=2)
    ARCHIVED = value(code="archived", display_name="Archived", sort_order=3)



class CatalogDenseLifecycle(Lifecycle[CatalogDenseStateEntity]):
    """draft → staged → archived."""


    _template = (
        Lifecycle().state(CatalogDenseStateEntity.DRAFT).to(CatalogDenseStateEntity.STAGED).initial().state(CatalogDenseStateEntity.STAGED).to(CatalogDenseStateEntity.ARCHIVED).intermediate().state(CatalogDenseStateEntity.ARCHIVED).final()
    )
