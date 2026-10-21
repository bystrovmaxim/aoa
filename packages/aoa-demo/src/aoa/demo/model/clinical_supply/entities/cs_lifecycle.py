# packages/aoa-demo/src/aoa/demo/model/clinical_supply/entities/cs_lifecycle.py
from pydantic import Field

from aoa.action_machine.domain import (
    BaseStateEntity,
    Lifecycle,
    StateVocabulary,
)


class ClinicalSupplyStateEntity(BaseStateEntity):
    """Status of the ClinicalSupply axis."""

    sort_order: int = Field(default=0, description="Presentation order")


class ClinicalSupplyLifecycle(Lifecycle, StateVocabulary):
    """Small linear lifecycle for sample rows."""

    DRAFT = ClinicalSupplyStateEntity(code="draft", display_name="Draft", sort_order=1)
    ACTIVE = ClinicalSupplyStateEntity(code="active", display_name="Active", sort_order=2)
    RETIRED = ClinicalSupplyStateEntity(code="retired", display_name="Retired", sort_order=3)

    _template = (
        Lifecycle().state(DRAFT).to(ACTIVE).initial().state(ACTIVE).to(RETIRED).intermediate().state(RETIRED).final()
    )
