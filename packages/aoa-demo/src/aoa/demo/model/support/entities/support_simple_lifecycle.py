# packages/aoa-demo/src/aoa/demo/model/support/entities/support_simple_lifecycle.py
"""Minimal lifecycle for sparse support-graph demo."""

from pydantic import Field

from aoa.action_machine.domain import (
    BaseStateEntity,
    Lifecycle,
    StateVocabulary,
)


class SupportSparseStateEntity(BaseStateEntity):
    """Status of the SupportSparse axis."""

    sort_order: int = Field(default=0, description="Presentation order")


class SupportSparseLifecycle(Lifecycle, StateVocabulary):
    """intake → working → done."""

    INTAKE = SupportSparseStateEntity(code="intake", display_name="Intake", sort_order=1)
    WORKING = SupportSparseStateEntity(code="working", display_name="Working", sort_order=2)
    DONE = SupportSparseStateEntity(code="done", display_name="Done", sort_order=3)

    _template = (
        Lifecycle().state(INTAKE).to(WORKING).initial().state(WORKING).to(DONE).intermediate().state(DONE).final()
    )
