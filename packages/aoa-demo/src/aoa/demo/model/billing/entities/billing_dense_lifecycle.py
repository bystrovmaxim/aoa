# packages/aoa-demo/src/aoa/demo/model/billing/entities/billing_dense_lifecycle.py
# pylint: disable=undefined-variable  # the class-name alias is the declaration surface
"""Tiny lifecycles for expanded billing ER demo rows."""

from pydantic import Field

from aoa.action_machine.domain import (
    BaseStateEntity,
    Lifecycle,
)


class BillingDenseStateEntity(BaseStateEntity):
    """Status of the BillingDense axis."""

    sort_order: int = Field(default=0, description="Presentation order")

    OPEN = BillingDenseStateEntity(code="open", display_name="Open", sort_order=1)  # noqa: F821
    FINALIZED = BillingDenseStateEntity(code="finalized", display_name="Finalized", sort_order=2)  # noqa: F821



class BillingDenseLifecycle(Lifecycle[BillingDenseStateEntity]):
    """open → finalized (single terminal)."""


    _template = Lifecycle().state(BillingDenseStateEntity.OPEN).to(BillingDenseStateEntity.FINALIZED).initial().state(BillingDenseStateEntity.FINALIZED).final()


class BillingPipelineStateEntity(BaseStateEntity):
    """Status of the BillingPipeline axis."""

    sort_order: int = Field(default=0, description="Presentation order")

    STAGED = BillingPipelineStateEntity(code="staged", display_name="Staged", sort_order=1)  # noqa: F821
    VALIDATED = BillingPipelineStateEntity(code="validated", display_name="Validated", sort_order=2)  # noqa: F821
    EXPORTED = BillingPipelineStateEntity(code="exported", display_name="Exported", sort_order=3)  # noqa: F821



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
