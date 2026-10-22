# packages/aoa-demo/src/aoa/demo/model/billing/entities/billing_multi_lifecycle_table_entities.py
# pylint: disable=undefined-variable  # the class-name alias is the declaration surface
"""Demo entities with two or three distinct lifecycle-typed fields (ERD / sidebar stress samples).

Each :class:`~aoa.action_machine.domain.lifecycle.Lifecycle` subclass uses a different-sized
template (1–4 transitions in a single terminal chain) and field names reflect settlement /
dispute / treasury language rather than generic ``lifecycle_2`` placeholders.
"""

from __future__ import annotations

from pydantic import Field

from aoa.action_machine.domain import (
    BaseCoreEntity,
    BaseStateEntity,
    Lifecycle,
)
from aoa.action_machine.intents.entity import entity
from aoa.demo.model.billing.domain import BillingDomain
from aoa.demo.model.dictionaries.entities.currency_enum import CurrencyEnumEntity


class CounterpartyLinkageStateEntity(BaseStateEntity):
    """Status of the CounterpartyLinkage axis."""

    sort_order: int = Field(default=0, description="Presentation order")

    UNLINKED = CounterpartyLinkageStateEntity(code="unlinked", display_name="Unlinked", sort_order=1)  # noqa: F821
    VERIFIED = CounterpartyLinkageStateEntity(code="verified", display_name="Verified", sort_order=2)  # noqa: F821



class CounterpartyLinkageLifecycle(Lifecycle[CounterpartyLinkageStateEntity]):
    """Two states, **one** transition: counterparty still needs KYC ring alignment."""


    _template = Lifecycle().state(CounterpartyLinkageStateEntity.UNLINKED).to(CounterpartyLinkageStateEntity.VERIFIED).initial().state(CounterpartyLinkageStateEntity.VERIFIED).final()


class LedgerPostingWaveStateEntity(BaseStateEntity):
    """Status of the LedgerPostingWave axis."""

    sort_order: int = Field(default=0, description="Presentation order")

    QUEUED = LedgerPostingWaveStateEntity(code="queued", display_name="Queued", sort_order=1)  # noqa: F821
    POSTED = LedgerPostingWaveStateEntity(code="posted", display_name="Posted", sort_order=2)  # noqa: F821
    RECONCILED = LedgerPostingWaveStateEntity(code="reconciled", display_name="Reconciled", sort_order=3)  # noqa: F821



class LedgerPostingWaveLifecycle(Lifecycle[LedgerPostingWaveStateEntity]):
    """Three states, **two** transitions: GL wave for a clearing batch."""


    _template = (
        Lifecycle()
        .state(LedgerPostingWaveStateEntity.QUEUED)
        .to(LedgerPostingWaveStateEntity.POSTED)
        .initial()
        .state(LedgerPostingWaveStateEntity.POSTED)
        .to(LedgerPostingWaveStateEntity.RECONCILED)
        .intermediate()
        .state(LedgerPostingWaveStateEntity.RECONCILED)
        .final()
    )


class SchemeDisputeClockStateEntity(BaseStateEntity):
    """Status of the SchemeDisputeClock axis."""

    sort_order: int = Field(default=0, description="Presentation order")

    NOTICE_RECEIVED = SchemeDisputeClockStateEntity(  # noqa: F821
        code="notice_received", display_name="Notice received", sort_order=1
    )
    EVIDENCE_WINDOW = SchemeDisputeClockStateEntity(  # noqa: F821
        code="evidence_window", display_name="Evidence window", sort_order=2
    )
    RULING_PENDING = SchemeDisputeClockStateEntity(code="ruling_pending", display_name="Ruling pending", sort_order=3)  # noqa: F821
    CLOSED = SchemeDisputeClockStateEntity(code="closed", display_name="Closed", sort_order=4)  # noqa: F821



class SchemeDisputeClockLifecycle(Lifecycle[SchemeDisputeClockStateEntity]):
    """Four states, **three** transitions: card-network dispute window."""


    _template = (
        Lifecycle()
        .state(SchemeDisputeClockStateEntity.NOTICE_RECEIVED)
        .to(SchemeDisputeClockStateEntity.EVIDENCE_WINDOW)
        .initial()
        .state(SchemeDisputeClockStateEntity.EVIDENCE_WINDOW)
        .to(SchemeDisputeClockStateEntity.RULING_PENDING)
        .intermediate()
        .state(SchemeDisputeClockStateEntity.RULING_PENDING)
        .to(SchemeDisputeClockStateEntity.CLOSED)
        .intermediate()
        .state(SchemeDisputeClockStateEntity.CLOSED)
        .final()
    )


class TreasuryCutoverProgramStateEntity(BaseStateEntity):
    """Status of the TreasuryCutoverProgram axis."""

    sort_order: int = Field(default=0, description="Presentation order")

    BLUEPRINT = TreasuryCutoverProgramStateEntity(code="blueprint", display_name="Blueprint", sort_order=1)  # noqa: F821
    DRY_RUN = TreasuryCutoverProgramStateEntity(code="dry_run", display_name="Dry run", sort_order=2)  # noqa: F821
    CANARY = TreasuryCutoverProgramStateEntity(code="canary", display_name="Canary", sort_order=3)  # noqa: F821
    FULL_CUT = TreasuryCutoverProgramStateEntity(code="full_cut", display_name="Full cut", sort_order=4)  # noqa: F821
    STEADY = TreasuryCutoverProgramStateEntity(code="steady", display_name="Steady state", sort_order=5)  # noqa: F821



class TreasuryCutoverProgramLifecycle(Lifecycle[TreasuryCutoverProgramStateEntity]):
    """Five states, **four** transitions: staged treasury rail cutover."""


    _template = (
        Lifecycle()
        .state(TreasuryCutoverProgramStateEntity.BLUEPRINT)
        .to(TreasuryCutoverProgramStateEntity.DRY_RUN)
        .initial()
        .state(TreasuryCutoverProgramStateEntity.DRY_RUN)
        .to(TreasuryCutoverProgramStateEntity.CANARY)
        .intermediate()
        .state(TreasuryCutoverProgramStateEntity.CANARY)
        .to(TreasuryCutoverProgramStateEntity.FULL_CUT)
        .intermediate()
        .state(TreasuryCutoverProgramStateEntity.FULL_CUT)
        .to(TreasuryCutoverProgramStateEntity.STEADY)
        .intermediate()
        .state(TreasuryCutoverProgramStateEntity.STEADY)
        .final()
    )


class NostroLiquiditySweepStateEntity(BaseStateEntity):
    """Status of the NostroLiquiditySweep axis."""

    sort_order: int = Field(default=0, description="Presentation order")

    SWEEP_PLANNED = NostroLiquiditySweepStateEntity(code="sweep_planned", display_name="Sweep planned", sort_order=1)  # noqa: F821
    SWEEP_SENT = NostroLiquiditySweepStateEntity(code="sweep_sent", display_name="Sweep sent", sort_order=2)  # noqa: F821
    SWEEP_ACKNOWLEDGED = NostroLiquiditySweepStateEntity(  # noqa: F821
        code="sweep_acknowledged", display_name="Sweep acknowledged", sort_order=3
    )



class NostroLiquiditySweepLifecycle(Lifecycle[NostroLiquiditySweepStateEntity]):
    """Three states, **two** transitions: nostro sweep (distinct labels from ledger posting wave)."""


    _template = (
        Lifecycle()
        .state(NostroLiquiditySweepStateEntity.SWEEP_PLANNED)
        .to(NostroLiquiditySweepStateEntity.SWEEP_SENT)
        .initial()
        .state(NostroLiquiditySweepStateEntity.SWEEP_SENT)
        .to(NostroLiquiditySweepStateEntity.SWEEP_ACKNOWLEDGED)
        .intermediate()
        .state(NostroLiquiditySweepStateEntity.SWEEP_ACKNOWLEDGED)
        .final()
    )


@entity(
    description="Issuer-facing dispute clock plus counterparty linkage (dual lifecycle columns)",
    domain=BillingDomain,
)
class IssuerDisputeWorkbenchCoreEntity(BaseCoreEntity):
    id: str = Field(description="Workbench bundle id")
    scheme_dispute_clock_lifecycle: SchemeDisputeClockLifecycle = Field(
        description="Network dispute timeline (notice → evidence → ruling → closure)",
    )
    counterparty_linkage_lifecycle: CounterpartyLinkageLifecycle = Field(
        description="Whether the counterparty legal ring is verified for this case",
    )

    legal_entity_ref: str = Field(description="Debtor / posting-company anchor")
    currency_iso: CurrencyEnumEntity = Field(description="Declared ISO-4217 money unit")
    case_reference: str = Field(description="Issuer case reference visible to ops")


@entity(
    description="Treasury cutover program tracked beside nostro sweep confirmation (dual lifecycles)",
    domain=BillingDomain,
)
class TreasuryCutoverBundleCoreEntity(BaseCoreEntity):
    id: str = Field(description="Cutover bundle id")
    rail_cutover_program_lifecycle: TreasuryCutoverProgramLifecycle = Field(
        description="Staged activation of a new settlement rail",
    )
    nostro_liquidity_sweep_lifecycle: NostroLiquiditySweepLifecycle = Field(
        description="Liquidity sweep status against nostro mirrors",
    )

    legal_entity_ref: str = Field(description="Debtor / posting-company anchor")
    currency_iso: CurrencyEnumEntity = Field(description="Declared ISO-4217 money unit")
    corridor_code: str = Field(description="Treasury corridor identifier")


@entity(
    description="Reconciliation audit with KYC ring, GL wave, and scheme dispute mesh (triple lifecycle)",
    domain=BillingDomain,
)
class MultiRingSettlementAuditCoreEntity(BaseCoreEntity):
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
    currency_iso: CurrencyEnumEntity = Field(description="Declared ISO-4217 money unit")
    audit_window_code: str = Field(description="Named reconciliation window (e.g. EOD-Europe)")
