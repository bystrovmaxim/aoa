# src/maxitor/samples/assurance_portfolio/entities/ap_evidence_carrier_stub.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.assurance_portfolio.domain import AssurancePortfolioDomain
from maxitor.samples.assurance_portfolio.entities.ap_lifecycle import AssurancePortfolioLifecycle
from maxitor.samples.assurance_portfolio.entities.ap_reference_axes import AssuranceEvidenceKindAxisEntity


@entity(description="Polymorphic-lite attachment header (fk_table analogue omitted deliberately)", domain=AssurancePortfolioDomain)
class AssuranceEvidenceCarrierStubEntity(BaseEntity):
    id: str = Field(description="Evidence carrier row id")
    lifecycle: AssurancePortfolioLifecycle = Field(description="Evidence carrier lifecycle")

    evidence_kind_axis: Annotated[
        AssociationOne[AssuranceEvidenceKindAxisEntity],
        NoInverse(),
    ] = Rel(description="Evidence media format")  # type: ignore[assignment]


AssuranceEvidenceCarrierStubEntity.model_rebuild()
