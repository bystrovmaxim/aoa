# packages/aoa-demo/src/aoa/demo/model/support/entities/support_simple_lifecycle.py
# pylint: disable=undefined-variable  # the class-name alias is the declaration surface
"""Minimal lifecycle for sparse support-graph demo."""

from pydantic import Field

from aoa.action_machine.domain import (
    BaseStateEntity,
    Lifecycle,
)


class SupportSparseStateEntity(BaseStateEntity):
    """Status of the SupportSparse axis."""

    sort_order: int = Field(default=0, description="Presentation order")

    INTAKE = SupportSparseStateEntity(code="intake", display_name="Intake", sort_order=1)  # noqa: F821
    WORKING = SupportSparseStateEntity(code="working", display_name="Working", sort_order=2)  # noqa: F821
    DONE = SupportSparseStateEntity(code="done", display_name="Done", sort_order=3)  # noqa: F821



class SupportSparseLifecycle(Lifecycle[SupportSparseStateEntity]):
    """intake → working → done."""


    _template = (
        Lifecycle().state(SupportSparseStateEntity.INTAKE).to(SupportSparseStateEntity.WORKING).initial().state(SupportSparseStateEntity.WORKING).to(SupportSparseStateEntity.DONE).intermediate().state(SupportSparseStateEntity.DONE).final()
    )
