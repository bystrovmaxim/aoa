# src/maxitor/samples/billing/entities/__init__.py
from __future__ import annotations

from maxitor.samples.billing.entities.arbitration_brief_stub import ArbitrationBriefStubEntity
from maxitor.samples.billing.entities.billing_canonical_row_artifact import BillingCanonicalRowArtifactEntity
from maxitor.samples.billing.entities.billing_dense_lifecycle import BillingDenseLifecycle, BillingPipelineLifecycle
from maxitor.samples.billing.entities.billing_file_ingest_manifest import BillingFileIngestManifestEntity
from maxitor.samples.billing.entities.billing_mesh_chargeback_ingest import BillingChargebackIngestCorrelateEntity
from maxitor.samples.billing.entities.billing_mesh_parse_interchange import BillingParseInterchangeBridgeEntity
from maxitor.samples.billing.entities.billing_parse_pass import BillingParsePassEntity
from maxitor.samples.billing.entities.billing_payout_plan import BillingPayoutPlanEntity
from maxitor.samples.billing.entities.billing_sat_acquirer_integrity import AcquirerIntegrityCheckEntity
from maxitor.samples.billing.entities.billing_sat_cash_apply_hint import CashApplicationHintEntity
from maxitor.samples.billing.entities.billing_sat_duplicate_ledger import DuplicateSuppressionLedgerEntity
from maxitor.samples.billing.entities.billing_sat_fee_schedule_ptr import MerchantFeeSchedulePointerEntity
from maxitor.samples.billing.entities.billing_sat_fx_residual import FxResidualTagEntity
from maxitor.samples.billing.entities.billing_sat_interchange_slice import InterchangeAssessmentSliceEntity
from maxitor.samples.billing.entities.billing_sat_ledger_mirror_offset import LedgerMirrorOffsetEntity
from maxitor.samples.billing.entities.billing_sat_narrative_correction import NarrativeCorrectionEntity
from maxitor.samples.billing.entities.billing_sat_profit_center_slice import ProfitCenterContributionEntity
from maxitor.samples.billing.entities.billing_sat_regulatory_ptr import RegulatorySubmissionPointerEntity
from maxitor.samples.billing.entities.billing_sat_ripple_correction import SettlementRippleCorrectionEntity
from maxitor.samples.billing.entities.billing_sat_tax_remit_stub import TaxRemittanceAdviceEntity
from maxitor.samples.billing.entities.billing_sweep_instruction import BillingSweepInstructionEntity
from maxitor.samples.billing.entities.chargeback_ticket import ChargebackTicketEntity
from maxitor.samples.billing.entities.funding_window_hint import FundingWindowHintEntity
from maxitor.samples.billing.entities.payment_event_log import PaymentEventLogEntity
from maxitor.samples.billing.entities.payment_lifecycle import PaymentEventLifecycle
from maxitor.samples.billing.entities.retrieval_evidence_bundle import RetrievalEvidenceBundleEntity

# Deferred forward-ref resolution (import cycles: parse_pass <-> FX/narrative/canonical spine).
BillingParsePassEntity.model_rebuild()

# Deferred: ``InterchangeAssessmentSliceEntity.chargeback_ingest_correlate`` avoids import cycle
# (mesh chargeback ingest imports ``ChargebackTicketEntity``, which imports this slice module).
InterchangeAssessmentSliceEntity.model_rebuild()

# Deferred: ``CashApplicationHintEntity.arbitration_brief`` uses a forward ref to
# ``ArbitrationBriefStubEntity``; rebuild after the package imports resolve the billing import cycle.
CashApplicationHintEntity.model_rebuild()

__all__ = [
    "AcquirerIntegrityCheckEntity",
    "ArbitrationBriefStubEntity",
    "BillingCanonicalRowArtifactEntity",
    "BillingChargebackIngestCorrelateEntity",
    "BillingDenseLifecycle",
    "BillingFileIngestManifestEntity",
    "BillingParseInterchangeBridgeEntity",
    "BillingParsePassEntity",
    "BillingPayoutPlanEntity",
    "BillingPipelineLifecycle",
    "BillingSweepInstructionEntity",
    "CashApplicationHintEntity",
    "ChargebackTicketEntity",
    "DuplicateSuppressionLedgerEntity",
    "FundingWindowHintEntity",
    "FxResidualTagEntity",
    "InterchangeAssessmentSliceEntity",
    "LedgerMirrorOffsetEntity",
    "MerchantFeeSchedulePointerEntity",
    "NarrativeCorrectionEntity",
    "PaymentEventLifecycle",
    "PaymentEventLogEntity",
    "ProfitCenterContributionEntity",
    "RegulatorySubmissionPointerEntity",
    "RetrievalEvidenceBundleEntity",
    "SettlementRippleCorrectionEntity",
    "TaxRemittanceAdviceEntity",
]
