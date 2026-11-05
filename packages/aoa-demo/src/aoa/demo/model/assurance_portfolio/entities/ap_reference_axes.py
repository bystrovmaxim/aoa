# packages/aoa-demo/src/aoa/demo/model/assurance_portfolio/entities/ap_reference_axes.py
from __future__ import annotations

from pydantic import Field

from aoa.action_machine.domain import BaseCoreEntity
from aoa.action_machine.intents.entity import entity
from aoa.demo.model.assurance_portfolio.entities.ap_lifecycle import AssurancePortfolioLifecycle
from aoa.demo.model.assurance_portfolio.resources.storage import AssurancePortfolioStorage


@entity(description="Lifecycle axis for credential posture (user_status analogue)", resource=AssurancePortfolioStorage)
class AssuranceAccountPhaseAxisCoreEntity(BaseCoreEntity):
    id: str = Field(description="Account phase axis id")
    lifecycle: AssurancePortfolioLifecycle = Field(description="Axis lifecycle")

    scenario_ref: str = Field(description="Scenario / release train reference tag")
    expectation_grade: str = Field(description="Tolerance band moniker for auditors")
    evidence_locker_id: str = Field(description="Immutable evidence bundle locator")
    audit_locale: str = Field(description="Regulatory framing geography code")
    automation_vendor: str = Field(description="Runner / harness vendor label")
    flaky_budget_pct: float = Field(description="Accepted flake-rate envelope percent", ge=0, le=100)


@entity(description="Named duty template bucket (role catalogue analogue)", resource=AssurancePortfolioStorage)
class AssuranceDutyTemplateAxisCoreEntity(BaseCoreEntity):
    id: str = Field(description="Duty axis id")
    lifecycle: AssurancePortfolioLifecycle = Field(description="Duty axis lifecycle")

    scenario_ref: str = Field(description="Scenario / release train reference tag")
    expectation_grade: str = Field(description="Tolerance band moniker for auditors")
    evidence_locker_id: str = Field(description="Immutable evidence bundle locator")
    audit_locale: str = Field(description="Regulatory framing geography code")
    automation_vendor: str = Field(description="Runner / harness vendor label")
    flaky_budget_pct: float = Field(description="Accepted flake-rate envelope percent", ge=0, le=100)


@entity(description="Atomic privilege grain (fine right analogue)", resource=AssurancePortfolioStorage)
class AssurancePrivilegeGrainAxisCoreEntity(BaseCoreEntity):
    id: str = Field(description="Privilege grain id")
    lifecycle: AssurancePortfolioLifecycle = Field(description="Privilege axis lifecycle")

    scenario_ref: str = Field(description="Scenario / release train reference tag")
    expectation_grade: str = Field(description="Tolerance band moniker for auditors")
    evidence_locker_id: str = Field(description="Immutable evidence bundle locator")
    audit_locale: str = Field(description="Regulatory framing geography code")
    automation_vendor: str = Field(description="Runner / harness vendor label")
    flaky_budget_pct: float = Field(description="Accepted flake-rate envelope percent", ge=0, le=100)


@entity(description="Requirement taxonomy discriminator", resource=AssurancePortfolioStorage)
class AssuranceExpectationGenreAxisCoreEntity(BaseCoreEntity):
    id: str = Field(description="Expectation genre id")
    lifecycle: AssurancePortfolioLifecycle = Field(description="Genre axis lifecycle")

    scenario_ref: str = Field(description="Scenario / release train reference tag")
    expectation_grade: str = Field(description="Tolerance band moniker for auditors")
    evidence_locker_id: str = Field(description="Immutable evidence bundle locator")
    audit_locale: str = Field(description="Regulatory framing geography code")
    automation_vendor: str = Field(description="Runner / harness vendor label")
    flaky_budget_pct: float = Field(description="Accepted flake-rate envelope percent", ge=0, le=100)


@entity(description="Requirement maturity runway states", resource=AssurancePortfolioStorage)
class AssuranceExpectationPhaseAxisCoreEntity(BaseCoreEntity):
    id: str = Field(description="Expectation phase axis id")
    lifecycle: AssurancePortfolioLifecycle = Field(description="Phase axis lifecycle")

    scenario_ref: str = Field(description="Scenario / release train reference tag")
    expectation_grade: str = Field(description="Tolerance band moniker for auditors")
    evidence_locker_id: str = Field(description="Immutable evidence bundle locator")
    audit_locale: str = Field(description="Regulatory framing geography code")
    automation_vendor: str = Field(description="Runner / harness vendor label")
    flaky_budget_pct: float = Field(description="Accepted flake-rate envelope percent", ge=0, le=100)


@entity(description="Depth tier along specification spine (spec_level analogue)", resource=AssurancePortfolioStorage)
class AssuranceSpecificationDepthAxisCoreEntity(BaseCoreEntity):
    id: str = Field(description="Specification depth tier id")
    lifecycle: AssurancePortfolioLifecycle = Field(description="Depth axis lifecycle")

    scenario_ref: str = Field(description="Scenario / release train reference tag")
    expectation_grade: str = Field(description="Tolerance band moniker for auditors")
    evidence_locker_id: str = Field(description="Immutable evidence bundle locator")
    audit_locale: str = Field(description="Regulatory framing geography code")
    automation_vendor: str = Field(description="Runner / harness vendor label")
    flaky_budget_pct: float = Field(description="Accepted flake-rate envelope percent", ge=0, le=100)


@entity(description="Delegated task intent flavours (assignment_type analogue)", resource=AssurancePortfolioStorage)
class AssuranceDelegationIntentAxisCoreEntity(BaseCoreEntity):
    id: str = Field(description="Delegation intent id")
    lifecycle: AssurancePortfolioLifecycle = Field(description="Delegation intent axis lifecycle")

    scenario_ref: str = Field(description="Scenario / release train reference tag")
    expectation_grade: str = Field(description="Tolerance band moniker for auditors")
    evidence_locker_id: str = Field(description="Immutable evidence bundle locator")
    audit_locale: str = Field(description="Regulatory framing geography code")
    automation_vendor: str = Field(description="Runner / harness vendor label")
    flaky_budget_pct: float = Field(description="Accepted flake-rate envelope percent", ge=0, le=100)


@entity(description="Workstream checkpoint labels (assignment_status analogue)", resource=AssurancePortfolioStorage)
class AssuranceCheckpointToneAxisCoreEntity(BaseCoreEntity):
    id: str = Field(description="Checkpoint tone id")
    lifecycle: AssurancePortfolioLifecycle = Field(description="Checkpoint tone axis lifecycle")

    scenario_ref: str = Field(description="Scenario / release train reference tag")
    expectation_grade: str = Field(description="Tolerance band moniker for auditors")
    evidence_locker_id: str = Field(description="Immutable evidence bundle locator")
    audit_locale: str = Field(description="Regulatory framing geography code")
    automation_vendor: str = Field(description="Runner / harness vendor label")
    flaky_budget_pct: float = Field(description="Accepted flake-rate envelope percent", ge=0, le=100)


@entity(description="Attachment carrier formats (attachment_type analogue)", resource=AssurancePortfolioStorage)
class AssuranceEvidenceKindAxisCoreEntity(BaseCoreEntity):
    id: str = Field(description="Evidence carrier kind id")
    lifecycle: AssurancePortfolioLifecycle = Field(description="Evidence axis lifecycle")

    scenario_ref: str = Field(description="Scenario / release train reference tag")
    expectation_grade: str = Field(description="Tolerance band moniker for auditors")
    evidence_locker_id: str = Field(description="Immutable evidence bundle locator")
    audit_locale: str = Field(description="Regulatory framing geography code")
    automation_vendor: str = Field(description="Runner / harness vendor label")
    flaky_budget_pct: float = Field(description="Accepted flake-rate envelope percent", ge=0, le=100)


AssuranceAccountPhaseAxisCoreEntity.model_rebuild()
AssuranceDutyTemplateAxisCoreEntity.model_rebuild()
AssurancePrivilegeGrainAxisCoreEntity.model_rebuild()
AssuranceExpectationGenreAxisCoreEntity.model_rebuild()
AssuranceExpectationPhaseAxisCoreEntity.model_rebuild()
AssuranceSpecificationDepthAxisCoreEntity.model_rebuild()
AssuranceDelegationIntentAxisCoreEntity.model_rebuild()
AssuranceCheckpointToneAxisCoreEntity.model_rebuild()
AssuranceEvidenceKindAxisCoreEntity.model_rebuild()
