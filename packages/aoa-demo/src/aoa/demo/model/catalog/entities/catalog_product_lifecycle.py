# packages/aoa-demo/src/aoa/demo/model/catalog/entities/catalog_product_lifecycle.py
"""Lifecycle graph for a catalog SKU row (sample)."""

from pydantic import Field

from aoa.action_machine.domain import (
    BaseStateEntity,
    Lifecycle,
    StateVocabulary,
)


class CatalogProductStateEntity(BaseStateEntity):
    """Status of the CatalogProduct axis."""

    sort_order: int = Field(default=0, description="Presentation order")


class CatalogProductLifecycle(Lifecycle, StateVocabulary):
    """Three states: draft → active → retired."""

    DRAFT = CatalogProductStateEntity(code="draft", display_name="Draft", sort_order=1)
    ACTIVE = CatalogProductStateEntity(code="active", display_name="Active", sort_order=2)
    RETIRED = CatalogProductStateEntity(code="retired", display_name="Retired", sort_order=3)

    _template = (
        Lifecycle().state(DRAFT).to(ACTIVE).initial().state(ACTIVE).to(RETIRED).intermediate().state(RETIRED).final()
    )
