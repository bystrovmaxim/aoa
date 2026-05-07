# src/maxitor/samples/assurance_portfolio/entities/ap_reference_axes.py
from __future__ import annotations

from pydantic import Field

from action_machine.domain import BaseEntity
from action_machine.intents.entity import entity
from maxitor.samples.assurance_portfolio.domain import AssurancePortfolioDomain
from maxitor.samples.assurance_portfolio.entities.ap_lifecycle import AssurancePortfolioLifecycle


@entity(description="Lifecycle axis for credential posture (user_status analogue)", domain=AssurancePortfolioDomain)
class AssuranceAccountPhaseAxisEntity(BaseEntity):
    lifecycle: AssurancePortfolioLifecycle = Field(description="Axis lifecycle")
    id: str = Field(description="Account phase axis id")


@entity(description="Named duty template bucket (role catalogue analogue)", domain=AssurancePortfolioDomain)
class AssuranceDutyTemplateAxisEntity(BaseEntity):
    lifecycle: AssurancePortfolioLifecycle = Field(description="Duty axis lifecycle")
    id: str = Field(description="Duty axis id")


@entity(description="Atomic privilege grain (fine right analogue)", domain=AssurancePortfolioDomain)
class AssurancePrivilegeGrainAxisEntity(BaseEntity):
    lifecycle: AssurancePortfolioLifecycle = Field(description="Privilege axis lifecycle")
    id: str = Field(description="Privilege grain id")


@entity(description="Requirement taxonomy discriminator", domain=AssurancePortfolioDomain)
class AssuranceExpectationGenreAxisEntity(BaseEntity):
    lifecycle: AssurancePortfolioLifecycle = Field(description="Genre axis lifecycle")
    id: str = Field(description="Expectation genre id")


@entity(description="Requirement maturity runway states", domain=AssurancePortfolioDomain)
class AssuranceExpectationPhaseAxisEntity(BaseEntity):
    lifecycle: AssurancePortfolioLifecycle = Field(description="Phase axis lifecycle")
    id: str = Field(description="Expectation phase axis id")


@entity(description="Depth tier along specification spine (spec_level analogue)", domain=AssurancePortfolioDomain)
class AssuranceSpecificationDepthAxisEntity(BaseEntity):
    lifecycle: AssurancePortfolioLifecycle = Field(description="Depth axis lifecycle")
    id: str = Field(description="Specification depth tier id")


@entity(description="Delegated task intent flavours (assignment_type analogue)", domain=AssurancePortfolioDomain)
class AssuranceDelegationIntentAxisEntity(BaseEntity):
    lifecycle: AssurancePortfolioLifecycle = Field(description="Delegation intent axis lifecycle")
    id: str = Field(description="Delegation intent id")


@entity(description="Workstream checkpoint labels (assignment_status analogue)", domain=AssurancePortfolioDomain)
class AssuranceCheckpointToneAxisEntity(BaseEntity):
    lifecycle: AssurancePortfolioLifecycle = Field(description="Checkpoint tone axis lifecycle")
    id: str = Field(description="Checkpoint tone id")


@entity(description="Attachment carrier formats (attachment_type analogue)", domain=AssurancePortfolioDomain)
class AssuranceEvidenceKindAxisEntity(BaseEntity):
    lifecycle: AssurancePortfolioLifecycle = Field(description="Evidence axis lifecycle")
    id: str = Field(description="Evidence carrier kind id")


AssuranceAccountPhaseAxisEntity.model_rebuild()
AssuranceDutyTemplateAxisEntity.model_rebuild()
AssurancePrivilegeGrainAxisEntity.model_rebuild()
AssuranceExpectationGenreAxisEntity.model_rebuild()
AssuranceExpectationPhaseAxisEntity.model_rebuild()
AssuranceSpecificationDepthAxisEntity.model_rebuild()
AssuranceDelegationIntentAxisEntity.model_rebuild()
AssuranceCheckpointToneAxisEntity.model_rebuild()
AssuranceEvidenceKindAxisEntity.model_rebuild()
