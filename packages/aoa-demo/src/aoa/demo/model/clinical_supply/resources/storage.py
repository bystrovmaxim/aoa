# packages/aoa-demo/src/aoa/demo/model/clinical_supply/resources/storage.py
"""ClinicalSupplyStorage — the store that holds the clinical supply domain's entities."""

from __future__ import annotations

from aoa.action_machine.intents.entities import entities
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources import BaseResource, BaseStorage
from aoa.demo.model.clinical_supply.entities.cs_care_site_unit import ClinicalCareSiteUnitCoreEntity
from aoa.demo.model.clinical_supply.entities.cs_consumable_sku_row import ClinicalConsumableSkuCoreEntity
from aoa.demo.model.clinical_supply.entities.cs_geographic_anchor import ClinicalGeographicAnchorCoreEntity
from aoa.demo.model.clinical_supply.entities.cs_inbound_shipment_ticket import ClinicalInboundShipmentTicketCoreEntity
from aoa.demo.model.clinical_supply.entities.cs_inbound_transport_binding import (
    ClinicalInboundTransportBindingCoreEntity,
)
from aoa.demo.model.clinical_supply.entities.cs_material_anchor import ClinicalMaterialAnchorCoreEntity
from aoa.demo.model.clinical_supply.entities.cs_outbound_parcel_line import ClinicalOutboundParcelLineDetailEntity
from aoa.demo.model.clinical_supply.entities.cs_outbound_parcel_wave import ClinicalOutboundParcelWaveCoreEntity
from aoa.demo.model.clinical_supply.entities.cs_ownership_anchor import ClinicalOwnershipAnchorCoreEntity
from aoa.demo.model.clinical_supply.entities.cs_packing_anchor import ClinicalPackingAnchorCoreEntity
from aoa.demo.model.clinical_supply.entities.cs_partner_hub import ClinicalPartnerHubCoreEntity
from aoa.demo.model.clinical_supply.entities.cs_partner_org_projection import ClinicalPartnerOrgProjectionCoreEntity
from aoa.demo.model.clinical_supply.entities.cs_partner_person_projection import (
    ClinicalPartnerPersonProjectionCoreEntity,
)
from aoa.demo.model.clinical_supply.entities.cs_transport_anchor import ClinicalTransportAnchorCoreEntity


@meta(description="Stores the clinical supply model (stub)")
@entities(
    ClinicalCareSiteUnitCoreEntity,
    ClinicalConsumableSkuCoreEntity,
    ClinicalGeographicAnchorCoreEntity,
    ClinicalInboundShipmentTicketCoreEntity,
    ClinicalInboundTransportBindingCoreEntity,
    ClinicalMaterialAnchorCoreEntity,
    ClinicalOutboundParcelLineDetailEntity,
    ClinicalOutboundParcelWaveCoreEntity,
    ClinicalOwnershipAnchorCoreEntity,
    ClinicalPackingAnchorCoreEntity,
    ClinicalPartnerHubCoreEntity,
    ClinicalPartnerOrgProjectionCoreEntity,
    ClinicalPartnerPersonProjectionCoreEntity,
    ClinicalTransportAnchorCoreEntity,
)
class ClinicalSupplyStorage(BaseStorage):
    """Hold the clinical supply domain's entities; the demo never opens it."""

    @classmethod
    def get_wrapper_class(cls) -> type[BaseResource] | None:
        """No wrapper: a nested action may use this resource as it is."""
        return None
