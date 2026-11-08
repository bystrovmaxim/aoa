# packages/aoa-demo/src/aoa/demo/model/assurance_portfolio/resources/storage.py
"""AssurancePortfolioStorage — the store that holds the assurance portfolio domain's entities."""

from __future__ import annotations

from aoa.action_machine.intents.entities import entities
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources import BaseResource, BaseStorage
from aoa.demo.model.assurance_portfolio.entities.ap_actor_duty_coupling import AssuranceActorDutyCouplingCoreEntity
from aoa.demo.model.assurance_portfolio.entities.ap_campaign_wave_banner import AssuranceCampaignWaveBannerCoreEntity
from aoa.demo.model.assurance_portfolio.entities.ap_delegated_work_ticket import AssuranceDelegatedWorkTicketCoreEntity
from aoa.demo.model.assurance_portfolio.entities.ap_duty_privilege_bridge import AssuranceDutyPrivilegeBridgeCoreEntity
from aoa.demo.model.assurance_portfolio.entities.ap_evidence_carrier_stub import AssuranceEvidenceCarrierStubCoreEntity
from aoa.demo.model.assurance_portfolio.entities.ap_execution_attempt_ticket import (
    AssuranceExecutionAttemptTicketCoreEntity,
)
from aoa.demo.model.assurance_portfolio.entities.ap_expectation_catalog_stub import (
    AssuranceExpectationCatalogStubCoreEntity,
)
from aoa.demo.model.assurance_portfolio.entities.ap_expectation_outline_node import (
    AssuranceExpectationOutlineNodeCoreEntity,
)
from aoa.demo.model.assurance_portfolio.entities.ap_facility_actor import AssuranceFacilityActorCoreEntity
from aoa.demo.model.assurance_portfolio.entities.ap_instruction_expectation_anchor import (
    AssuranceInstructionExpectationAnchorCoreEntity,
)
from aoa.demo.model.assurance_portfolio.entities.ap_portfolio_lane_stub import AssurancePortfolioLaneStubCoreEntity
from aoa.demo.model.assurance_portfolio.entities.ap_portfolio_workspace_coupler import (
    AssurancePortfolioWorkspaceCouplerCoreEntity,
)
from aoa.demo.model.assurance_portfolio.entities.ap_reference_axes import (
    AssuranceAccountPhaseAxisCoreEntity,
    AssuranceCheckpointToneAxisCoreEntity,
    AssuranceDelegationIntentAxisCoreEntity,
    AssuranceDutyTemplateAxisCoreEntity,
    AssuranceEvidenceKindAxisCoreEntity,
    AssuranceExpectationGenreAxisCoreEntity,
    AssuranceExpectationPhaseAxisCoreEntity,
    AssurancePrivilegeGrainAxisCoreEntity,
    AssuranceSpecificationDepthAxisCoreEntity,
)
from aoa.demo.model.assurance_portfolio.entities.ap_regulated_expectation_row import (
    AssuranceRegulatedExpectationRowDetailEntity,
)
from aoa.demo.model.assurance_portfolio.entities.ap_scenario_instruction_line import (
    AssuranceScenarioInstructionLineDetailEntity,
)
from aoa.demo.model.assurance_portfolio.entities.ap_scenario_sheet import AssuranceScenarioSheetCoreEntity
from aoa.demo.model.assurance_portfolio.entities.ap_wave_execution_slot import AssuranceWaveExecutionSlotCoreEntity
from aoa.demo.model.assurance_portfolio.entities.ap_wave_seat_coupling import AssuranceWaveSeatCouplingCoreEntity
from aoa.demo.model.assurance_portfolio.entities.ap_workspace_program_stub import (
    AssuranceWorkspaceProgramStubCoreEntity,
)
from aoa.demo.model.assurance_portfolio.entities.ap_workspace_seat_grant import AssuranceWorkspaceSeatGrantCoreEntity


@meta(description="Stores the assurance portfolio model (stub)")
@entities(
    AssuranceActorDutyCouplingCoreEntity,
    AssuranceCampaignWaveBannerCoreEntity,
    AssuranceDelegatedWorkTicketCoreEntity,
    AssuranceDutyPrivilegeBridgeCoreEntity,
    AssuranceEvidenceCarrierStubCoreEntity,
    AssuranceExecutionAttemptTicketCoreEntity,
    AssuranceExpectationCatalogStubCoreEntity,
    AssuranceExpectationOutlineNodeCoreEntity,
    AssuranceFacilityActorCoreEntity,
    AssuranceInstructionExpectationAnchorCoreEntity,
    AssurancePortfolioLaneStubCoreEntity,
    AssurancePortfolioWorkspaceCouplerCoreEntity,
    AssuranceAccountPhaseAxisCoreEntity,
    AssuranceDutyTemplateAxisCoreEntity,
    AssurancePrivilegeGrainAxisCoreEntity,
    AssuranceExpectationGenreAxisCoreEntity,
    AssuranceExpectationPhaseAxisCoreEntity,
    AssuranceSpecificationDepthAxisCoreEntity,
    AssuranceDelegationIntentAxisCoreEntity,
    AssuranceCheckpointToneAxisCoreEntity,
    AssuranceEvidenceKindAxisCoreEntity,
    AssuranceRegulatedExpectationRowDetailEntity,
    AssuranceScenarioInstructionLineDetailEntity,
    AssuranceScenarioSheetCoreEntity,
    AssuranceWaveExecutionSlotCoreEntity,
    AssuranceWaveSeatCouplingCoreEntity,
    AssuranceWorkspaceProgramStubCoreEntity,
    AssuranceWorkspaceSeatGrantCoreEntity,
)
class AssurancePortfolioStorage(BaseStorage):
    """Hold the assurance portfolio domain's entities; the demo never opens it."""

    @classmethod
    def get_wrapper_class(cls) -> type[BaseResource] | None:
        """No wrapper: a nested action may use this resource as it is."""
        return None
