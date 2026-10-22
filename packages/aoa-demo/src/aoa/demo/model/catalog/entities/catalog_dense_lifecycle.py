# packages/aoa-demo/src/aoa/demo/model/catalog/entities/catalog_dense_lifecycle.py
# pylint: disable=undefined-variable  # the class-name alias is the declaration surface
"""Lifecycles for expanded catalog SKU graph demo."""

from pydantic import Field

from aoa.action_machine.domain import (
    BaseStateEntity,
    Lifecycle,
)


class CatalogDenseStateEntity(BaseStateEntity):
    """Status of the CatalogDense axis."""

    sort_order: int = Field(default=0, description="Presentation order")

    DRAFT = CatalogDenseStateEntity(code="draft", display_name="Draft", sort_order=1)  # noqa: F821
    STAGED = CatalogDenseStateEntity(code="staged", display_name="Staged", sort_order=2)  # noqa: F821
    ARCHIVED = CatalogDenseStateEntity(code="archived", display_name="Archived", sort_order=3)  # noqa: F821



class CatalogDenseLifecycle(Lifecycle[CatalogDenseStateEntity]):
    """draft → staged → archived."""


    _template = (
        Lifecycle().state(CatalogDenseStateEntity.DRAFT).to(CatalogDenseStateEntity.STAGED).initial().state(CatalogDenseStateEntity.STAGED).to(CatalogDenseStateEntity.ARCHIVED).intermediate().state(CatalogDenseStateEntity.ARCHIVED).final()
    )
