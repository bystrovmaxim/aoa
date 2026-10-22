# packages/aoa-demo/src/aoa/demo/model/clinical_supply/entities/cs_lifecycle.py
# pylint: disable=undefined-variable  # the class-name alias is the declaration surface
from pydantic import Field

from aoa.action_machine.domain import (
    BaseStateEntity,
    Lifecycle,
)


class ClinicalSupplyStateEntity(BaseStateEntity):
    """Status of the ClinicalSupply axis."""

    sort_order: int = Field(default=0, description="Presentation order")

    DRAFT = ClinicalSupplyStateEntity(code="draft", display_name="Draft", sort_order=1)  # noqa: F821
    ACTIVE = ClinicalSupplyStateEntity(code="active", display_name="Active", sort_order=2)  # noqa: F821
    RETIRED = ClinicalSupplyStateEntity(code="retired", display_name="Retired", sort_order=3)  # noqa: F821



class ClinicalSupplyLifecycle(Lifecycle[ClinicalSupplyStateEntity]):
    """Small linear lifecycle for sample rows."""


    _template = (
        Lifecycle().state(ClinicalSupplyStateEntity.DRAFT).to(ClinicalSupplyStateEntity.ACTIVE).initial().state(ClinicalSupplyStateEntity.ACTIVE).to(ClinicalSupplyStateEntity.RETIRED).intermediate().state(ClinicalSupplyStateEntity.RETIRED).final()
    )
