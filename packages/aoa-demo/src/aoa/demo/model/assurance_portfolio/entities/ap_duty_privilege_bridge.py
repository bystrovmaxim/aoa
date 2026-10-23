# packages/aoa-demo/src/aoa/demo/model/assurance_portfolio/entities/ap_duty_privilege_bridge.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseCoreEntity, NoInverse
from aoa.action_machine.intents.entity import entity
from aoa.demo.model.assurance_portfolio.domain import AssurancePortfolioDomain
from aoa.demo.model.assurance_portfolio.entities.ap_lifecycle import AssurancePortfolioLifecycle
from aoa.demo.model.assurance_portfolio.entities.ap_reference_axes import (
    AssuranceDutyTemplateAxisCoreEntity,
    AssurancePrivilegeGrainAxisCoreEntity,
)


@entity(
    description="Join between duties and fine-grained privileges (role_has_right analogue)",
    domain=AssurancePortfolioDomain,
)
class AssuranceDutyPrivilegeBridgeCoreEntity(BaseCoreEntity):
    id: str = Field(description="Bridge id")
    lifecycle: AssurancePortfolioLifecycle = Field(description="Bridge lifecycle")

    scenario_ref: str = Field(description="Scenario / release train reference tag")
    expectation_grade: str = Field(description="Tolerance band moniker for auditors")
    evidence_locker_id: str = Field(description="Immutable evidence bundle locator")
    audit_locale: str = Field(description="Regulatory framing geography code")
    automation_vendor: str = Field(description="Runner / harness vendor label")
    flaky_budget_pct: float = Field(description="Accepted flake-rate envelope percent", ge=0, le=100)
    duty_axis: Annotated[
        AssociationOne[AssuranceDutyTemplateAxisCoreEntity],
        NoInverse(),
    ] = Field(
        description="Duty template anchoring grant"
    )

    privilege_grain: Annotated[
        AssociationOne[AssurancePrivilegeGrainAxisCoreEntity],
        NoInverse(),
    ] = Field(
        description="Granted privilege grain"
    )


AssuranceDutyPrivilegeBridgeCoreEntity.model_rebuild()
