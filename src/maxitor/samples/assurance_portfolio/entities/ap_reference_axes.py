# src/maxitor/samples/assurance_portfolio/entities/ap_reference_axes.py
from __future__ import annotations

from pydantic import Field

from action_machine.domain import BaseEntity
from action_machine.intents.entity import entity
from maxitor.samples.assurance_portfolio.domain import AssurancePortfolioDomain
from maxitor.samples.assurance_portfolio.entities.ap_lifecycle import AssurancePortfolioLifecycle


@entity(description="Lifecycle axis for credential posture (user_status analogue)", domain=AssurancePortfolioDomain)
class AssuranceAccountPhaseAxisEntity(BaseEntity):
    id: str = Field(description="Account phase axis id")
    lifecycle: AssurancePortfolioLifecycle = Field(description="Axis lifecycle")


@entity(description="Named duty template bucket (role catalogue analogue)", domain=AssurancePortfolioDomain)
class AssuranceDutyTemplateAxisEntity(BaseEntity):
    id: str = Field(description="Duty axis id")
    lifecycle: AssurancePortfolioLifecycle = Field(description="Duty axis lifecycle")


@entity(description="Atomic privilege grain (fine right analogue)", domain=AssurancePortfolioDomain)
class AssurancePrivilegeGrainAxisEntity(BaseEntity):
    id: str = Field(description="Privilege grain id")
    lifecycle: AssurancePortfolioLifecycle = Field(description="Privilege axis lifecycle")


@entity(description="Requirement taxonomy discriminator", domain=AssurancePortfolioDomain)
class AssuranceExpectationGenreAxisEntity(BaseEntity):
    id: str = Field(description="Expectation genre id")
    lifecycle: AssurancePortfolioLifecycle = Field(description="Genre axis lifecycle")


@entity(description="Requirement maturity runway states", domain=AssurancePortfolioDomain)
class AssuranceExpectationPhaseAxisEntity(BaseEntity):
    id: str = Field(description="Expectation phase axis id")
    lifecycle: AssurancePortfolioLifecycle = Field(description="Phase axis lifecycle")


@entity(description="Depth tier along specification spine (spec_level analogue)", domain=AssurancePortfolioDomain)
class AssuranceSpecificationDepthAxisEntity(BaseEntity):
    id: str = Field(description="Specification depth tier id")
    lifecycle: AssurancePortfolioLifecycle = Field(description="Depth axis lifecycle")


@entity(description="Delegated task intent flavours (assignment_type analogue)", domain=AssurancePortfolioDomain)
class AssuranceDelegationIntentAxisEntity(BaseEntity):
    id: str = Field(description="Delegation intent id")
    lifecycle: AssurancePortfolioLifecycle = Field(description="Delegation intent axis lifecycle")


@entity(description="Workstream checkpoint labels (assignment_status analogue)", domain=AssurancePortfolioDomain)
class AssuranceCheckpointToneAxisEntity(BaseEntity):
    id: str = Field(description="Checkpoint tone id")
    lifecycle: AssurancePortfolioLifecycle = Field(description="Checkpoint tone axis lifecycle")


@entity(description="Attachment carrier formats (attachment_type analogue)", domain=AssurancePortfolioDomain)
class AssuranceEvidenceKindAxisEntity(BaseEntity):
    id: str = Field(description="Evidence carrier kind id")
    lifecycle: AssurancePortfolioLifecycle = Field(description="Evidence axis lifecycle")


AssuranceAccountPhaseAxisEntity.model_rebuild()
AssuranceDutyTemplateAxisEntity.model_rebuild()
AssurancePrivilegeGrainAxisEntity.model_rebuild()
AssuranceExpectationGenreAxisEntity.model_rebuild()
AssuranceExpectationPhaseAxisEntity.model_rebuild()
AssuranceSpecificationDepthAxisEntity.model_rebuild()
AssuranceDelegationIntentAxisEntity.model_rebuild()
AssuranceCheckpointToneAxisEntity.model_rebuild()
AssuranceEvidenceKindAxisEntity.model_rebuild()
