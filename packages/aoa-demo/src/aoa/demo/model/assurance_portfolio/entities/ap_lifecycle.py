# packages/aoa-demo/src/aoa/demo/model/assurance_portfolio/entities/ap_lifecycle.py
from pydantic import Field

from aoa.action_machine.domain import (
    BaseStateEntity,
    Lifecycle,
    StateVocabulary,
)


class AssurancePortfolioStateEntity(BaseStateEntity):
    """Status of the AssurancePortfolio axis."""

    sort_order: int = Field(default=0, description="Presentation order")


class AssurancePortfolioLifecycle(Lifecycle, StateVocabulary):
    """Linear bookkeeping lifecycle for seeded portfolio rows."""

    INTAKE = AssurancePortfolioStateEntity(code="intake", display_name="Intake", sort_order=1)
    STEADY = AssurancePortfolioStateEntity(code="steady", display_name="Steady", sort_order=2)
    FROZEN = AssurancePortfolioStateEntity(code="frozen", display_name="Frozen", sort_order=3)

    _template = (
        Lifecycle().state(INTAKE).to(STEADY).initial().state(STEADY).to(FROZEN).intermediate().state(FROZEN).final()
    )
