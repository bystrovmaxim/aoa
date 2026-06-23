# packages/aoa-examples/src/aoa/examples/model/billing/entities/billing_multi_lifecycle_table_entities.py
"""Demo entities with two or three distinct lifecycle-typed fields (ERD / sidebar stress samples).

Each :class:`~aoa.action_machine.domain.lifecycle.Lifecycle` subclass uses a different-sized
template (1–4 transitions in a single terminal chain) and field names reflect settlement /
dispute / treasury language rather than generic ``lifecycle_2`` placeholders.
"""

from __future__ import annotations

from pydantic import Field

from aoa.action_machine.domain import BaseEntity, Lifecycle
from aoa.action_machine.intents.entity import entity
from aoa.examples.model.billing.domain import BillingDomain


class CounterpartyLinkageLifecycle(Lifecycle):
    """Two states, **one** transition: counterparty still needs KYC ring alignment."""

    _template = Lifecycle().state("unlinked", "Unlinked").to("verified").initial().state("verified", "Verified").final()


class LedgerPostingWaveLifecycle(Lifecycle):
    """Three states, **two** transitions: GL wave for a clearing batch."""

    _template = (
        Lifecycle()
        .state("queued", "Queued")
        .to("posted")
        .initial()
        .state("posted", "Posted")
        .to("reconciled")
        .intermediate()
        .state("reconciled", "Reconciled")
        .final()
    )


class SchemeDisputeClockLifecycle(Lifecycle):
    """Four states, **three** transitions: card-network dispute window."""

    _template = (
        Lifecycle()
        .state("notice_received", "Notice received")
        .to("evidence_window")
        .initial()
        .state("evidence_window", "Evidence window")
        .to("ruling_pending")
        .intermediate()
        .state("ruling_pending", "Ruling pending")
        .to("closed")
        .intermediate()
        .state("closed", "Closed")
        .final()
    )


class TreasuryCutoverProgramLifecycle(Lifecycle):
    """Five states, **four** transitions: staged treasury rail cutover."""

    _template = (
        Lifecycle()
        .state("blueprint", "Blueprint")
        .to("dry_run")
        .initial()
        .state("dry_run", "Dry run")
        .to("canary")
        .intermediate()
        .state("canary", "Canary")
        .to("full_cut")
        .intermediate()
        .state("full_cut", "Full cut")
        .to("steady")
        .intermediate()
        .state("steady", "Steady state")
        .final()
    )


class NostroLiquiditySweepLifecycle(Lifecycle):
    """Three states, **two** transitions: nostro sweep (distinct labels from ledger posting wave)."""

    _template = (
        Lifecycle()
        .state("sweep_planned", "Sweep planned")
        .to("sweep_sent")
        .initial()
        .state("sweep_sent", "Sweep sent")
        .to("sweep_acknowledged")
        .intermediate()
        .state("sweep_acknowledged", "Sweep acknowledged")
        .final()
    )


@entity(
    description="Issuer-facing dispute clock plus counterparty linkage (dual lifecycle columns)",
    domain=BillingDomain,
)
class IssuerDisputeWorkbenchEntity(BaseEntity):
    id: str = Field(description="Workbench bundle id")
    scheme_dispute_clock_lifecycle: SchemeDisputeClockLifecycle = Field(
        description="Network dispute timeline (notice → evidence → ruling → closure)",
    )
    counterparty_linkage_lifecycle: CounterpartyLinkageLifecycle = Field(
        description="Whether the counterparty legal ring is verified for this case",
    )

    legal_entity_ref: str = Field(description="Debtor / posting-company anchor")
    currency_iso: str = Field(description="Declared ISO-4217 money unit")
    case_reference: str = Field(description="Issuer case reference visible to ops")


@entity(
    description="Treasury cutover program tracked beside nostro sweep confirmation (dual lifecycles)",
    domain=BillingDomain,
)
class TreasuryCutoverBundleEntity(BaseEntity):
    id: str = Field(description="Cutover bundle id")
    rail_cutover_program_lifecycle: TreasuryCutoverProgramLifecycle = Field(
        description="Staged activation of a new settlement rail",
    )
    nostro_liquidity_sweep_lifecycle: NostroLiquiditySweepLifecycle = Field(
        description="Liquidity sweep status against nostro mirrors",
    )

    legal_entity_ref: str = Field(description="Debtor / posting-company anchor")
    currency_iso: str = Field(description="Declared ISO-4217 money unit")
    corridor_code: str = Field(description="Treasury corridor identifier")


@entity(
    description="Reconciliation audit with KYC ring, GL wave, and scheme dispute mesh (triple lifecycle)",
    domain=BillingDomain,
)
class MultiRingSettlementAuditEntity(BaseEntity):
    id: str = Field(description="Audit run id")
    counterparty_kyc_ring_lifecycle: CounterpartyLinkageLifecycle = Field(
        description="Counterparty verification ring for this reconciliation",
    )
    ledger_posting_wave_lifecycle: LedgerPostingWaveLifecycle = Field(
        description="Posting wave for the audited clearing batch",
    )
    scheme_dispute_mesh_lifecycle: SchemeDisputeClockLifecycle = Field(
        description="Parallel scheme dispute clock if chargebacks overlap the run",
    )

    legal_entity_ref: str = Field(description="Debtor / posting-company anchor")
    currency_iso: str = Field(description="Declared ISO-4217 money unit")
    audit_window_code: str = Field(description="Named reconciliation window (e.g. EOD-Europe)")
