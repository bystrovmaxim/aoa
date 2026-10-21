# packages/aoa-demo/src/aoa/demo/model/billing/entities/billing_multi_lifecycle_table_entities.py
"""Demo entities with two or three distinct lifecycle-typed fields (ERD / sidebar stress samples).

Each :class:`~aoa.action_machine.domain.lifecycle.Lifecycle` subclass uses a different-sized
template (1–4 transitions in a single terminal chain) and field names reflect settlement /
dispute / treasury language rather than generic ``lifecycle_2`` placeholders.
"""

from __future__ import annotations

from pydantic import Field

from aoa.action_machine.domain import (
    BaseEntity,
    BaseStateEntity,
    Lifecycle,
    StateVocabulary,
)
from aoa.action_machine.intents.entity import entity
from aoa.demo.model.billing.domain import BillingDomain


class CounterpartyLinkageStateEntity(BaseStateEntity):
    """Status of the CounterpartyLinkage axis."""

    sort_order: int = Field(default=0, description="Presentation order")


class CounterpartyLinkageLifecycle(Lifecycle, StateVocabulary):
    """Two states, **one** transition: counterparty still needs KYC ring alignment."""

    UNLINKED = CounterpartyLinkageStateEntity(code="unlinked", display_name="Unlinked", sort_order=1)
    VERIFIED = CounterpartyLinkageStateEntity(code="verified", display_name="Verified", sort_order=2)

    _template = Lifecycle().state(UNLINKED).to(VERIFIED).initial().state(VERIFIED).final()


class LedgerPostingWaveStateEntity(BaseStateEntity):
    """Status of the LedgerPostingWave axis."""

    sort_order: int = Field(default=0, description="Presentation order")


class LedgerPostingWaveLifecycle(Lifecycle, StateVocabulary):
    """Three states, **two** transitions: GL wave for a clearing batch."""

    QUEUED = LedgerPostingWaveStateEntity(code="queued", display_name="Queued", sort_order=1)
    POSTED = LedgerPostingWaveStateEntity(code="posted", display_name="Posted", sort_order=2)
    RECONCILED = LedgerPostingWaveStateEntity(code="reconciled", display_name="Reconciled", sort_order=3)

    _template = (
        Lifecycle()
        .state(QUEUED)
        .to(POSTED)
        .initial()
        .state(POSTED)
        .to(RECONCILED)
        .intermediate()
        .state(RECONCILED)
        .final()
    )


class SchemeDisputeClockStateEntity(BaseStateEntity):
    """Status of the SchemeDisputeClock axis."""

    sort_order: int = Field(default=0, description="Presentation order")


class SchemeDisputeClockLifecycle(Lifecycle, StateVocabulary):
    """Four states, **three** transitions: card-network dispute window."""

    NOTICE_RECEIVED = SchemeDisputeClockStateEntity(
        code="notice_received", display_name="Notice received", sort_order=1
    )
    EVIDENCE_WINDOW = SchemeDisputeClockStateEntity(
        code="evidence_window", display_name="Evidence window", sort_order=2
    )
    RULING_PENDING = SchemeDisputeClockStateEntity(code="ruling_pending", display_name="Ruling pending", sort_order=3)
    CLOSED = SchemeDisputeClockStateEntity(code="closed", display_name="Closed", sort_order=4)

    _template = (
        Lifecycle()
        .state(NOTICE_RECEIVED)
        .to(EVIDENCE_WINDOW)
        .initial()
        .state(EVIDENCE_WINDOW)
        .to(RULING_PENDING)
        .intermediate()
        .state(RULING_PENDING)
        .to(CLOSED)
        .intermediate()
        .state(CLOSED)
        .final()
    )


class TreasuryCutoverProgramStateEntity(BaseStateEntity):
    """Status of the TreasuryCutoverProgram axis."""

    sort_order: int = Field(default=0, description="Presentation order")


class TreasuryCutoverProgramLifecycle(Lifecycle, StateVocabulary):
    """Five states, **four** transitions: staged treasury rail cutover."""

    BLUEPRINT = TreasuryCutoverProgramStateEntity(code="blueprint", display_name="Blueprint", sort_order=1)
    DRY_RUN = TreasuryCutoverProgramStateEntity(code="dry_run", display_name="Dry run", sort_order=2)
    CANARY = TreasuryCutoverProgramStateEntity(code="canary", display_name="Canary", sort_order=3)
    FULL_CUT = TreasuryCutoverProgramStateEntity(code="full_cut", display_name="Full cut", sort_order=4)
    STEADY = TreasuryCutoverProgramStateEntity(code="steady", display_name="Steady state", sort_order=5)

    _template = (
        Lifecycle()
        .state(BLUEPRINT)
        .to(DRY_RUN)
        .initial()
        .state(DRY_RUN)
        .to(CANARY)
        .intermediate()
        .state(CANARY)
        .to(FULL_CUT)
        .intermediate()
        .state(FULL_CUT)
        .to(STEADY)
        .intermediate()
        .state(STEADY)
        .final()
    )


class NostroLiquiditySweepStateEntity(BaseStateEntity):
    """Status of the NostroLiquiditySweep axis."""

    sort_order: int = Field(default=0, description="Presentation order")


class NostroLiquiditySweepLifecycle(Lifecycle, StateVocabulary):
    """Three states, **two** transitions: nostro sweep (distinct labels from ledger posting wave)."""

    SWEEP_PLANNED = NostroLiquiditySweepStateEntity(code="sweep_planned", display_name="Sweep planned", sort_order=1)
    SWEEP_SENT = NostroLiquiditySweepStateEntity(code="sweep_sent", display_name="Sweep sent", sort_order=2)
    SWEEP_ACKNOWLEDGED = NostroLiquiditySweepStateEntity(
        code="sweep_acknowledged", display_name="Sweep acknowledged", sort_order=3
    )

    _template = (
        Lifecycle()
        .state(SWEEP_PLANNED)
        .to(SWEEP_SENT)
        .initial()
        .state(SWEEP_SENT)
        .to(SWEEP_ACKNOWLEDGED)
        .intermediate()
        .state(SWEEP_ACKNOWLEDGED)
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
