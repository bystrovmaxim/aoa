# packages/aoa-demo/src/aoa/demo/model/billing/entities/billing_dense_lifecycle.py
"""Tiny lifecycles for expanded billing ER demo rows."""

from pydantic import Field

from aoa.action_machine.domain import (
    BaseStateEntity,
    Lifecycle,
    value,
)


class BillingDenseStateEntity(BaseStateEntity):
    """Status of the BillingDense axis."""

    sort_order: int = Field(default=0, description="Presentation order")

    OPEN = value(code="open", display_name="Open", sort_order=1)
    FINALIZED = value(code="finalized", display_name="Finalized", sort_order=2)



class BillingDenseLifecycle(Lifecycle[BillingDenseStateEntity]):
    """open → finalized (single terminal)."""


    _template = Lifecycle().state(BillingDenseStateEntity.OPEN).to(BillingDenseStateEntity.FINALIZED).initial().state(BillingDenseStateEntity.FINALIZED).final()


class BillingPipelineStateEntity(BaseStateEntity):
    """Status of the BillingPipeline axis."""

    sort_order: int = Field(default=0, description="Presentation order")

    STAGED = value(code="staged", display_name="Staged", sort_order=1)
    VALIDATED = value(code="validated", display_name="Validated", sort_order=2)
    EXPORTED = value(code="exported", display_name="Exported", sort_order=3)



class BillingPipelineLifecycle(Lifecycle[BillingPipelineStateEntity]):
    """staged ingest pipeline markers."""


    _template = (
        Lifecycle()
        .state(BillingPipelineStateEntity.STAGED)
        .to(BillingPipelineStateEntity.VALIDATED)
        .initial()
        .state(BillingPipelineStateEntity.VALIDATED)
        .to(BillingPipelineStateEntity.EXPORTED)
        .intermediate()
        .state(BillingPipelineStateEntity.EXPORTED)
        .final()
    )
