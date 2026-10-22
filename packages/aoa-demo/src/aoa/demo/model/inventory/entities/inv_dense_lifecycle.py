# packages/aoa-demo/src/aoa/demo/model/inventory/entities/inv_dense_lifecycle.py
# pylint: disable=undefined-variable  # the class-name alias is the declaration surface
from pydantic import Field

from aoa.action_machine.domain import (
    BaseStateEntity,
    Lifecycle,
)


class InvDenseStateEntity(BaseStateEntity):
    """Status of the InvDense axis."""

    sort_order: int = Field(default=0, description="Presentation order")

    AVAILABLE = InvDenseStateEntity(code="available", display_name="Available", sort_order=1)  # noqa: F821
    COMMITTED = InvDenseStateEntity(code="committed", display_name="Committed", sort_order=2)  # noqa: F821
    DEPLETED = InvDenseStateEntity(code="depleted", display_name="Depleted", sort_order=3)  # noqa: F821



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

    RECEIPT = InvPipelineStateEntity(code="receipt", display_name="Receipt", sort_order=1)  # noqa: F821
    STAGING = InvPipelineStateEntity(code="staging", display_name="Staging", sort_order=2)  # noqa: F821
    ANCHORED = InvPipelineStateEntity(code="anchored", display_name="Anchored", sort_order=3)  # noqa: F821



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
