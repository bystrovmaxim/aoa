# packages/aoa-demo/src/aoa/demo/model/inventory/entities/inv_dense_lifecycle.py
# pylint: disable=undefined-variable  # the class-name alias is the declaration surface
from pydantic import Field

from aoa.action_machine.domain import (
    BaseStateEntity,
    Lifecycle,
    value,
)


class InvDenseStateEntity(BaseStateEntity):
    """Status of the InvDense axis."""

    sort_order: int = Field(default=0, description="Presentation order")

    AVAILABLE = value(code="available", display_name="Available", sort_order=1)
    COMMITTED = value(code="committed", display_name="Committed", sort_order=2)
    DEPLETED = value(code="depleted", display_name="Depleted", sort_order=3)



class InvDenseLifecycle(Lifecycle[InvDenseStateEntity]):
    """available → depleted."""


    _template = (
        Lifecycle()
        .state(InvDenseStateEntity.AVAILABLE)
        .to(InvDenseStateEntity.COMMITTED)
        .initial()
        .state(InvDenseStateEntity.COMMITTED)
        .to(InvDenseStateEntity.DEPLETED)
        .intermediate()
        .state(InvDenseStateEntity.DEPLETED)
        .final()
    )


class InvPipelineStateEntity(BaseStateEntity):
    """Status of the InvPipeline axis."""

    sort_order: int = Field(default=0, description="Presentation order")

    RECEIPT = value(code="receipt", display_name="Receipt", sort_order=1)
    STAGING = value(code="staging", display_name="Staging", sort_order=2)
    ANCHORED = value(code="anchored", display_name="Anchored", sort_order=3)



class InvPipelineLifecycle(Lifecycle[InvPipelineStateEntity]):
    """receipt → anchored."""


    _template = (
        Lifecycle()
        .state(InvPipelineStateEntity.RECEIPT)
        .to(InvPipelineStateEntity.STAGING)
        .initial()
        .state(InvPipelineStateEntity.STAGING)
        .to(InvPipelineStateEntity.ANCHORED)
        .intermediate()
        .state(InvPipelineStateEntity.ANCHORED)
        .final()
    )
