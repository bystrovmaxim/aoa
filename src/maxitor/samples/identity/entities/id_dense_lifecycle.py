# src/maxitor/samples/identity/entities/id_dense_lifecycle.py
from action_machine.domain import Lifecycle


class IdentityDenseLifecycle(Lifecycle):
    """registered → dormant."""

    _template = (
        Lifecycle()
        .state("registered", "Registered").to("active").initial()
        .state("active", "Active").to("dormant").intermediate()
        .state("dormant", "Dormant").final()
    )
