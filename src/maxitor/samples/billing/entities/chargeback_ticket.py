# src/maxitor/samples/billing/entities/chargeback_ticket.py
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import AssociationOne, BaseEntity, NoInverse, Rel
from action_machine.intents.entity import entity
from maxitor.samples.billing.domain import BillingDomain
from maxitor.samples.billing.entities.billing_dense_lifecycle import BillingDenseLifecycle
from maxitor.samples.billing.entities.billing_sat_interchange_slice import InterchangeAssessmentSliceEntity
from maxitor.samples.billing.entities.billing_sat_tax_remit_stub import TaxRemittanceAdviceEntity
from maxitor.samples.billing.entities.payment_event_log import PaymentEventLogEntity


@entity(description="Chargeback case opened on payment-event", domain=BillingDomain)
class ChargebackTicketEntity(BaseEntity):
    id: str = Field(description="Ticket id")
    lifecycle: BillingDenseLifecycle = Field(description="Dispute lifecycle")

    payment_event: Annotated[
        AssociationOne[PaymentEventLogEntity],
        NoInverse(),
    ] = Rel(description="Funding payment event anchor")  # type: ignore[assignment]

    interchange_assessment_slice: Annotated[
        AssociationOne[InterchangeAssessmentSliceEntity],
        NoInverse(),
    ] = Rel(description="Associated interchange assessment economics slice")  # type: ignore[assignment]

    tax_remit_advice: Annotated[
        AssociationOne[TaxRemittanceAdviceEntity],
        NoInverse(),
    ] = Rel(description="Associated tax remittance advice stub row")  # type: ignore[assignment]

    issuer_case_id: str = Field(description="Issuer or acquirer case identifier")
    network_reason_code: str = Field(description="Network standardized dispute reason code")
    opened_at_utc_iso: str = Field(description="Case opened timestamp (UTC ISO-8601)")
    provisional_credit_minor: int = Field(description="Provisional credit in minor currency units", ge=0)

    issuer_bin_country_iso: str = Field(description="ISO country inferred from BIN prefix")
    liability_shift_requested: bool = Field(description="Whether merchant seeks liability shift")
    representment_deadline_iso: str = Field(description="Last date to assemble counter-evidence")
    disputed_amount_minor: int = Field(description="Disputed amount in minor transactional currency", ge=0)
    cardholder_contact_locale: str = Field(description="Locale hint for outbound comms")

ChargebackTicketEntity.model_rebuild()
