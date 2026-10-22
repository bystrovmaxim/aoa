# packages/aoa-demo/src/aoa/demo/model/assurance_portfolio/entities/ap_lifecycle.py
# pylint: disable=undefined-variable  # the class-name alias is the declaration surface
from pydantic import Field

from aoa.action_machine.domain import (
    BaseStateEntity,
    Lifecycle,
)


class AssurancePortfolioStateEntity(BaseStateEntity):
    """Status of the AssurancePortfolio axis."""

    sort_order: int = Field(default=0, description="Presentation order")

    INTAKE = AssurancePortfolioStateEntity(code="intake", display_name="Intake", sort_order=1)  # noqa: F821
    STEADY = AssurancePortfolioStateEntity(code="steady", display_name="Steady", sort_order=2)  # noqa: F821
    FROZEN = AssurancePortfolioStateEntity(code="frozen", display_name="Frozen", sort_order=3)  # noqa: F821



class AssurancePortfolioLifecycle(Lifecycle[AssurancePortfolioStateEntity]):
    """Linear bookkeeping lifecycle for seeded portfolio rows."""


    _template = (
        Lifecycle().state(AssurancePortfolioStateEntity.INTAKE).to(AssurancePortfolioStateEntity.STEADY).initial().state(AssurancePortfolioStateEntity.STEADY).to(AssurancePortfolioStateEntity.FROZEN).intermediate().state(AssurancePortfolioStateEntity.FROZEN).final()
    )
