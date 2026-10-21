# packages/aoa-demo/src/aoa/demo/model/identity/entities/id_dense_lifecycle.py
from pydantic import Field

from aoa.action_machine.domain import (
    BaseStateEntity,
    Lifecycle,
    StateVocabulary,
)


class IdentityDenseStateEntity(BaseStateEntity):
    """Status of the IdentityDense axis."""

    sort_order: int = Field(default=0, description="Presentation order")


class IdentityDenseLifecycle(Lifecycle, StateVocabulary):
    """registered → dormant."""

    REGISTERED = IdentityDenseStateEntity(code="registered", display_name="Registered", sort_order=1)
    ACTIVE = IdentityDenseStateEntity(code="active", display_name="Active", sort_order=2)
    DORMANT = IdentityDenseStateEntity(code="dormant", display_name="Dormant", sort_order=3)

    _template = (
        Lifecycle()
        .state(REGISTERED)
        .to(ACTIVE)
        .initial()
        .state(ACTIVE)
        .to(DORMANT)
        .intermediate()
        .state(DORMANT)
        .final()
    )
