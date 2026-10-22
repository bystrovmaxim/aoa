# packages/aoa-demo/src/aoa/demo/model/catalog/entities/catalog_product_lifecycle.py
# pylint: disable=undefined-variable  # the class-name alias is the declaration surface
"""Lifecycle graph for a catalog SKU row (sample)."""

from pydantic import Field

from aoa.action_machine.domain import (
    BaseStateEntity,
    Lifecycle,
)


class CatalogProductStateEntity(BaseStateEntity):
    """Status of the CatalogProduct axis."""

    sort_order: int = Field(default=0, description="Presentation order")

    DRAFT = CatalogProductStateEntity(code="draft", display_name="Draft", sort_order=1)  # noqa: F821
    ACTIVE = CatalogProductStateEntity(code="active", display_name="Active", sort_order=2)  # noqa: F821
    RETIRED = CatalogProductStateEntity(code="retired", display_name="Retired", sort_order=3)  # noqa: F821



class CatalogProductLifecycle(Lifecycle[CatalogProductStateEntity]):
    """Three states: draft → active → retired."""


    _template = (
        Lifecycle().state(CatalogProductStateEntity.DRAFT).to(CatalogProductStateEntity.ACTIVE).initial().state(CatalogProductStateEntity.ACTIVE).to(CatalogProductStateEntity.RETIRED).intermediate().state(CatalogProductStateEntity.RETIRED).final()
    )
