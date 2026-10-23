# packages/aoa-demo/src/aoa/demo/model/clinical_supply/entities/cs_lifecycle.py
from pydantic import Field

from aoa.action_machine.domain import (
    BaseStateEntity,
    Lifecycle,
    value,
)


class ClinicalSupplyStateEntity(BaseStateEntity):
    """Status of the ClinicalSupply axis."""

    sort_order: int = Field(default=0, description="Presentation order")

    DRAFT = value(code="draft", display_name="Draft", sort_order=1)
    ACTIVE = value(code="active", display_name="Active", sort_order=2)
    RETIRED = value(code="retired", display_name="Retired", sort_order=3)



class ClinicalSupplyLifecycle(Lifecycle[ClinicalSupplyStateEntity]):
    """Small linear lifecycle for sample rows."""


    _template = (
        Lifecycle().state(ClinicalSupplyStateEntity.DRAFT).to(ClinicalSupplyStateEntity.ACTIVE).initial().state(ClinicalSupplyStateEntity.ACTIVE).to(ClinicalSupplyStateEntity.RETIRED).intermediate().state(ClinicalSupplyStateEntity.RETIRED).final()
    )
