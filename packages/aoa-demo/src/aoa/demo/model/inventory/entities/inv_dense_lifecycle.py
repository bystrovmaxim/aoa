# packages/aoa-demo/src/aoa/demo/model/inventory/entities/inv_dense_lifecycle.py
from pydantic import Field

from aoa.action_machine.domain import (
    BaseStateEntity,
    Lifecycle,
    StateVocabulary,
)


class InvDenseStateEntity(BaseStateEntity):
    """Status of the InvDense axis."""

    sort_order: int = Field(default=0, description="Presentation order")


class InvDenseLifecycle(Lifecycle, StateVocabulary):
    """available → depleted."""

    AVAILABLE = InvDenseStateEntity(code="available", display_name="Available", sort_order=1)
    COMMITTED = InvDenseStateEntity(code="committed", display_name="Committed", sort_order=2)
    DEPLETED = InvDenseStateEntity(code="depleted", display_name="Depleted", sort_order=3)

    _template = (
        Lifecycle()
        .state(AVAILABLE)
        .to(COMMITTED)
        .initial()
        .state(COMMITTED)
        .to(DEPLETED)
        .intermediate()
        .state(DEPLETED)
        .final()
    )


class InvPipelineStateEntity(BaseStateEntity):
    """Status of the InvPipeline axis."""

    sort_order: int = Field(default=0, description="Presentation order")


class InvPipelineLifecycle(Lifecycle, StateVocabulary):
    """receipt → anchored."""

    RECEIPT = InvPipelineStateEntity(code="receipt", display_name="Receipt", sort_order=1)
    STAGING = InvPipelineStateEntity(code="staging", display_name="Staging", sort_order=2)
    ANCHORED = InvPipelineStateEntity(code="anchored", display_name="Anchored", sort_order=3)

    _template = (
        Lifecycle()
        .state(RECEIPT)
        .to(STAGING)
        .initial()
        .state(STAGING)
        .to(ANCHORED)
        .intermediate()
        .state(ANCHORED)
        .final()
    )
