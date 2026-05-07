# src/maxitor/samples/assurance_portfolio/entities/ap_duty_privilege_bridge.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.assurance_portfolio.domain import AssurancePortfolioDomain
from maxitor.samples.assurance_portfolio.entities.ap_lifecycle import AssurancePortfolioLifecycle
from maxitor.samples.assurance_portfolio.entities.ap_reference_axes import (
    AssuranceDutyTemplateAxisEntity,
    AssurancePrivilegeGrainAxisEntity,
)


@entity(description="Join between duties and fine-grained privileges (role_has_right analogue)", domain=AssurancePortfolioDomain)
class AssuranceDutyPrivilegeBridgeEntity(BaseEntity):
    id: str = Field(description="Bridge id")
    lifecycle: AssurancePortfolioLifecycle = Field(description="Bridge lifecycle")

    scenario_ref: str = Field(description="Scenario / release train reference tag")
    expectation_grade: str = Field(description="Tolerance band moniker for auditors")
    evidence_locker_id: str = Field(description="Immutable evidence bundle locator")
    audit_locale: str = Field(description="Regulatory framing geography code")
    automation_vendor: str = Field(description="Runner / harness vendor label")
    flaky_budget_pct: float = Field(description="Accepted flake-rate envelope percent", ge=0, le=100)
    duty_axis: Annotated[
        AssociationOne[AssuranceDutyTemplateAxisEntity],
        NoInverse(),
    ] = Rel(description="Duty template anchoring grant")  # type: ignore[assignment]

    privilege_grain: Annotated[
        AssociationOne[AssurancePrivilegeGrainAxisEntity],
        NoInverse(),
    ] = Rel(description="Granted privilege grain")  # type: ignore[assignment]


AssuranceDutyPrivilegeBridgeEntity.model_rebuild()
