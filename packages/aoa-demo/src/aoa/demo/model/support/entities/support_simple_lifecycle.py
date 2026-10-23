# packages/aoa-demo/src/aoa/demo/model/support/entities/support_simple_lifecycle.py
# pylint: disable=undefined-variable  # the class-name alias is the declaration surface
"""Minimal lifecycle for sparse support-graph demo."""

from pydantic import Field

from aoa.action_machine.domain import (
    BaseStateEntity,
    Lifecycle,
    value,
)


class SupportSparseStateEntity(BaseStateEntity):
    """Status of the SupportSparse axis."""

    sort_order: int = Field(default=0, description="Presentation order")

    INTAKE = value(code="intake", display_name="Intake", sort_order=1)
    WORKING = value(code="working", display_name="Working", sort_order=2)
    DONE = value(code="done", display_name="Done", sort_order=3)



class SupportSparseLifecycle(Lifecycle[SupportSparseStateEntity]):
    """intake → working → done."""


    _template = (
        Lifecycle().state(SupportSparseStateEntity.INTAKE).to(SupportSparseStateEntity.WORKING).initial().state(SupportSparseStateEntity.WORKING).to(SupportSparseStateEntity.DONE).intermediate().state(SupportSparseStateEntity.DONE).final()
    )
