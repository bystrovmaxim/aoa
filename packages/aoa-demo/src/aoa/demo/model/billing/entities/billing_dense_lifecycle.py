# packages/aoa-demo/src/aoa/demo/model/billing/entities/billing_dense_lifecycle.py
"""Tiny lifecycles for expanded billing ER demo rows."""

from pydantic import Field

from aoa.action_machine.domain import (
    BaseStateEntity,
    Lifecycle,
    StateVocabulary,
)


class BillingDenseStateEntity(BaseStateEntity):
    """Status of the BillingDense axis."""

    sort_order: int = Field(default=0, description="Presentation order")


class BillingDenseLifecycle(Lifecycle, StateVocabulary):
    """open → finalized (single terminal)."""

    OPEN = BillingDenseStateEntity(code="open", display_name="Open", sort_order=1)
    FINALIZED = BillingDenseStateEntity(code="finalized", display_name="Finalized", sort_order=2)

    _template = Lifecycle().state(OPEN).to(FINALIZED).initial().state(FINALIZED).final()


class BillingPipelineStateEntity(BaseStateEntity):
    """Status of the BillingPipeline axis."""

    sort_order: int = Field(default=0, description="Presentation order")


class BillingPipelineLifecycle(Lifecycle, StateVocabulary):
    """staged ingest pipeline markers."""

    STAGED = BillingPipelineStateEntity(code="staged", display_name="Staged", sort_order=1)
    VALIDATED = BillingPipelineStateEntity(code="validated", display_name="Validated", sort_order=2)
    EXPORTED = BillingPipelineStateEntity(code="exported", display_name="Exported", sort_order=3)

    _template = (
        Lifecycle()
        .state(STAGED)
        .to(VALIDATED)
        .initial()
        .state(VALIDATED)
        .to(EXPORTED)
        .intermediate()
        .state(EXPORTED)
        .final()
    )
