# packages/aoa-demo/src/aoa/demo/model/databases/shop_database_storage.py
"""
ShopDatabaseStorage — the one database of the storefront, the support desk and inventory.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The demo's three domains kept their data in one database, each reaching it through
a resource of its own. A resource **is** a database, so that database is one
resource: ``ShopDatabaseStorage`` lists every entity of the storefront, the support
desk and inventory, and the model names no store at all. The domain of each entity
comes from the entity itself; the resource has none.

The SQL lifecycle methods are harmless no-ops: the demo never opens a connection.
Inherited ``close`` stays safe, and ``SqlStorage`` gives a nested action the same
wrapper the storefront resource gave it before the merge.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    store, support and inventory actions and entities
                 │
                 ▼
    ShopDatabaseStorage (SqlStorage)  ── one @entities list, one database
                 │
                 ▼
    resource_entity edges to every listed entity (protocol 2.0)

The relation check reads the entity's own domain, not this resource: a relation
between two of these entities, like any relation, needs no store to be named.
"""

from __future__ import annotations

from aoa.action_machine.intents.entities import entities
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.sql import SqlStorage
from aoa.demo.model.catalog.entities.catalog_availability_projection import AvailabilityProjectionCoreEntity
from aoa.demo.model.inventory.entities.inv_bin_coordinate_stub import BinCoordinateStubCoreEntity
from aoa.demo.model.inventory.entities.inv_crossdock_staging import CrossDockStagingCoreEntity
from aoa.demo.model.inventory.entities.inv_disposition_advice import DispositionAdviceCoreEntity
from aoa.demo.model.inventory.entities.inv_facility_warehouse import FacilityWarehouseCoreEntity
from aoa.demo.model.inventory.entities.inv_lot_age_bucket import LotAgeBucketCoreEntity
from aoa.demo.model.inventory.entities.inv_lot_freeze_flag import LotFreezeFlagCoreEntity
from aoa.demo.model.inventory.entities.inv_lot_quality_hold import LotQualityHoldCoreEntity
from aoa.demo.model.inventory.entities.inv_lot_snapshot_ledger import LotSnapshotLedgerCoreEntity
from aoa.demo.model.inventory.entities.inv_mesh_bin_age import InvBinAgeCorrelateCoreEntity
from aoa.demo.model.inventory.entities.inv_mesh_facility_crossdock import InvFacilityCrossdockBridgeCoreEntity
from aoa.demo.model.inventory.entities.inv_recall_signal import RecallSignalCoreEntity
from aoa.demo.model.inventory.entities.inv_storage_aisle_row import StorageAisleRowDetailEntity
from aoa.demo.model.store.entities.audit_log_entry import AuditLogEntryDetailEntity
from aoa.demo.model.store.entities.discount_application import DiscountApplicationCoreEntity
from aoa.demo.model.store.entities.fulfillment_task import FulfillmentTaskCoreEntity
from aoa.demo.model.store.entities.invoice_record import InvoiceRecordCoreEntity
from aoa.demo.model.store.entities.payment_authorization import PaymentAuthorizationCoreEntity
from aoa.demo.model.store.entities.payment_capture import PaymentCaptureCoreEntity
from aoa.demo.model.store.entities.refund_request import RefundRequestCoreEntity
from aoa.demo.model.store.entities.return_request import ReturnRequestCoreEntity
from aoa.demo.model.store.entities.sales_core import (
    CustomerAccountCoreEntity,
    SalesOrderCoreEntity,
    SalesOrderLineDetailEntity,
)
from aoa.demo.model.store.entities.shipment_parcel import ShipmentParcelCoreEntity
from aoa.demo.model.store.entities.shipment_tracking_event import ShipmentTrackingEventCoreEntity
from aoa.demo.model.store.entities.store_er_cycle_ping_pong import (
    StoreDirectedCyclePingCoreEntity,
    StoreDirectedCyclePongCoreEntity,
)
from aoa.demo.model.store.entities.store_line_backorder_eta import BackorderEtaFacetCoreEntity
from aoa.demo.model.store.entities.store_line_kit_explosion import KitExplosionLineDetailEntity
from aoa.demo.model.store.entities.store_line_pick_variance import PickVarianceRecordCoreEntity
from aoa.demo.model.store.entities.store_line_serial_trace import LineSerialLotTraceCoreEntity
from aoa.demo.model.store.entities.store_line_shipment_piece import LineShipmentPieceDetailEntity
from aoa.demo.model.store.entities.store_line_substitution_hist import SubstitutionHistoryCoreEntity
from aoa.demo.model.store.entities.store_line_warranty_offer import WarrantyOfferFacetCoreEntity
from aoa.demo.model.store.entities.store_loyalty_earn_projection import LoyaltyEarnProjectionCoreEntity
from aoa.demo.model.store.entities.store_mesh_customer_order_affinity import StoreCustomerOrderAffinityCoreEntity
from aoa.demo.model.store.entities.store_mesh_invoice_line_tie import StoreInvoiceLineTieCoreEntity
from aoa.demo.model.store.entities.store_mesh_line_parcel_pick import StoreLineParcelPickCoreEntity
from aoa.demo.model.store.entities.store_mesh_order_invoice_bridge import StoreOrderInvoiceBridgeCoreEntity
from aoa.demo.model.store.entities.store_mesh_order_parcel_handoff import StoreOrderParcelHandoffCoreEntity
from aoa.demo.model.store.entities.store_order_address_verification import AddressVerificationTrailCoreEntity
from aoa.demo.model.store.entities.store_order_channel_attribution import OrderChannelAttributionCoreEntity
from aoa.demo.model.store.entities.store_order_compliance_review import ComplianceReviewQueueCoreEntity
from aoa.demo.model.store.entities.store_order_deposit_allocation import DepositAllocationCoreEntity
from aoa.demo.model.store.entities.store_order_dual_entry_origin import OrderDualEntryOriginTraceCoreEntity
from aoa.demo.model.store.entities.store_order_fraud_challenge import FraudChallengeTicketCoreEntity
from aoa.demo.model.store.entities.store_order_geo_fence import OrderGeoFenceCoreEntity
from aoa.demo.model.store.entities.store_order_gift_wrap import GiftWrapAddonCoreEntity
from aoa.demo.model.store.entities.store_order_packing_slip import PackingSlipCoreEntity
from aoa.demo.model.store.entities.store_order_revenue_schedule import RevenueDeferralScheduleCoreEntity
from aoa.demo.model.store.entities.store_order_shipment_estimate import ShipmentEstimateCoreEntity
from aoa.demo.model.store.entities.store_order_split_bill import SplitBillAllocationCoreEntity
from aoa.demo.model.store.entities.store_order_tax_jurisdiction import OrderTaxJurisdictionSnapshotCoreEntity
from aoa.demo.model.store.entities.subscription import SubscriptionCoreEntity
from aoa.demo.model.store.entities.tax_line import TaxLineDetailEntity
from aoa.demo.model.support.entities.support_comment_thread_stub import SupportCommentThreadStubCoreEntity
from aoa.demo.model.support.entities.support_mesh_ticket_observer import SupportTicketParticipantPairCoreEntity
from aoa.demo.model.support.entities.support_participant_row import SupportParticipantCoreEntity
from aoa.demo.model.support.entities.support_sla_interval import SupportSlaIntervalCoreEntity
from aoa.demo.model.support.entities.support_ticket_aggregate import SupportTicketAggregateCoreEntity


@meta(description="The shop database — storefront, support desk and inventory (stub)")
@entities(
    AuditLogEntryDetailEntity,
    DiscountApplicationCoreEntity,
    FulfillmentTaskCoreEntity,
    InvoiceRecordCoreEntity,
    PaymentAuthorizationCoreEntity,
    PaymentCaptureCoreEntity,
    RefundRequestCoreEntity,
    ReturnRequestCoreEntity,
    CustomerAccountCoreEntity,
    SalesOrderCoreEntity,
    SalesOrderLineDetailEntity,
    ShipmentParcelCoreEntity,
    ShipmentTrackingEventCoreEntity,
    StoreDirectedCyclePingCoreEntity,
    StoreDirectedCyclePongCoreEntity,
    BackorderEtaFacetCoreEntity,
    KitExplosionLineDetailEntity,
    PickVarianceRecordCoreEntity,
    LineSerialLotTraceCoreEntity,
    LineShipmentPieceDetailEntity,
    SubstitutionHistoryCoreEntity,
    WarrantyOfferFacetCoreEntity,
    LoyaltyEarnProjectionCoreEntity,
    StoreCustomerOrderAffinityCoreEntity,
    StoreInvoiceLineTieCoreEntity,
    StoreLineParcelPickCoreEntity,
    StoreOrderInvoiceBridgeCoreEntity,
    StoreOrderParcelHandoffCoreEntity,
    AddressVerificationTrailCoreEntity,
    OrderChannelAttributionCoreEntity,
    ComplianceReviewQueueCoreEntity,
    DepositAllocationCoreEntity,
    OrderDualEntryOriginTraceCoreEntity,
    FraudChallengeTicketCoreEntity,
    OrderGeoFenceCoreEntity,
    GiftWrapAddonCoreEntity,
    PackingSlipCoreEntity,
    RevenueDeferralScheduleCoreEntity,
    ShipmentEstimateCoreEntity,
    SplitBillAllocationCoreEntity,
    OrderTaxJurisdictionSnapshotCoreEntity,
    SubscriptionCoreEntity,
    TaxLineDetailEntity,
    SupportCommentThreadStubCoreEntity,
    SupportTicketParticipantPairCoreEntity,
    SupportParticipantCoreEntity,
    SupportSlaIntervalCoreEntity,
    SupportTicketAggregateCoreEntity,
    AvailabilityProjectionCoreEntity,
    BinCoordinateStubCoreEntity,
    CrossDockStagingCoreEntity,
    DispositionAdviceCoreEntity,
    FacilityWarehouseCoreEntity,
    LotAgeBucketCoreEntity,
    LotFreezeFlagCoreEntity,
    LotQualityHoldCoreEntity,
    LotSnapshotLedgerCoreEntity,
    InvBinAgeCorrelateCoreEntity,
    InvFacilityCrossdockBridgeCoreEntity,
    RecallSignalCoreEntity,
    StorageAisleRowDetailEntity,
)
class ShopDatabaseStorage(SqlStorage):
    """
    AI-CORE-BEGIN
    ROLE: Database-free storage for the demo database shared by three domains.
    CONTRACT: Provide the SQL lifecycle without acquiring a connection, and list every entity the storefront, the support desk and inventory keep there.
    INVARIANTS: The class keeps its Storage kind; it declares no domain — the domains are its entities' domains.
    AI-CORE-END
    """

    def __init__(self, rollup: bool = False) -> None:
        """Preserve the SQL contract’s rollup configuration."""
        super().__init__(rollup=rollup)

    async def open(self) -> None:
        """Keep the database-free store ready for use."""
        return None

    async def begin(self) -> None:
        """Accept a transaction boundary without external state."""
        return None

    async def commit(self) -> None:
        """Finish the demo transaction without persistence."""
        return None

    async def rollback(self) -> None:
        """Finish the demo transaction without external writes."""
        return None
