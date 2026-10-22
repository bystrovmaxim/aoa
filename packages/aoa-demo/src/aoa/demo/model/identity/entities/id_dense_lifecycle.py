# packages/aoa-demo/src/aoa/demo/model/identity/entities/id_dense_lifecycle.py
# pylint: disable=undefined-variable  # the class-name alias is the declaration surface
from pydantic import Field

from aoa.action_machine.domain import (
    BaseStateEntity,
    Lifecycle,
)


class IdentityDenseStateEntity(BaseStateEntity):
    """Status of the IdentityDense axis."""

    sort_order: int = Field(default=0, description="Presentation order")

    REGISTERED = IdentityDenseStateEntity(code="registered", display_name="Registered", sort_order=1)  # noqa: F821
    ACTIVE = IdentityDenseStateEntity(code="active", display_name="Active", sort_order=2)  # noqa: F821
    DORMANT = IdentityDenseStateEntity(code="dormant", display_name="Dormant", sort_order=3)  # noqa: F821



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
