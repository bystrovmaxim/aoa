# src/maxitor/samples/assurance_portfolio/entities/ap_workspace_seat_grant.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.assurance_portfolio.domain import AssurancePortfolioDomain
from maxitor.samples.assurance_portfolio.entities.ap_facility_actor import AssuranceFacilityActorEntity
from maxitor.samples.assurance_portfolio.entities.ap_lifecycle import AssurancePortfolioLifecycle
from maxitor.samples.assurance_portfolio.entities.ap_workspace_program_stub import (
    AssuranceWorkspaceProgramStubEntity,
)


@entity(description="Actor ↔ workspace stewardship grant (test project role analogue)", domain=AssurancePortfolioDomain)
class AssuranceWorkspaceSeatGrantEntity(BaseEntity):
    id: str = Field(description="Seat grant id")
    lifecycle: AssurancePortfolioLifecycle = Field(description="Seat lifecycle")

    actor: Annotated[
        AssociationOne[AssuranceFacilityActorEntity],
        NoInverse(),
    ] = Rel(description="Seated actor")  # type: ignore[assignment]

    workspace_program: Annotated[
        AssociationOne[AssuranceWorkspaceProgramStubEntity],
        NoInverse(),
    ] = Rel(description="Subject workspace capsule")  # type: ignore[assignment]


AssuranceWorkspaceSeatGrantEntity.model_rebuild()
