# packages/aoa-demo/src/aoa/demo/model/identity/entities/id_dense_lifecycle.py
# pylint: disable=undefined-variable  # the class-name alias is the declaration surface
from pydantic import Field

from aoa.action_machine.domain import (
    BaseStateEntity,
    Lifecycle,
    value,
)


class IdentityDenseStateEntity(BaseStateEntity):
    """Status of the IdentityDense axis."""

    sort_order: int = Field(default=0, description="Presentation order")

    REGISTERED = value(code="registered", display_name="Registered", sort_order=1)
    ACTIVE = value(code="active", display_name="Active", sort_order=2)
    DORMANT = value(code="dormant", display_name="Dormant", sort_order=3)



class IdentityDenseLifecycle(Lifecycle[IdentityDenseStateEntity]):
    """registered → dormant."""


    _template = (
        Lifecycle()
        .state(IdentityDenseStateEntity.REGISTERED)
        .to(IdentityDenseStateEntity.ACTIVE)
        .initial()
        .state(IdentityDenseStateEntity.ACTIVE)
        .to(IdentityDenseStateEntity.DORMANT)
        .intermediate()
        .state(IdentityDenseStateEntity.DORMANT)
        .final()
    )
