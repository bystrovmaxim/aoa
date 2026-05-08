# src/maxitor/samples/inventory/entities/inv_dense_lifecycle.py
from action_machine.domain import Lifecycle


class InvDenseLifecycle(Lifecycle):
    """available → depleted."""

    _template = (
        Lifecycle()
        .state("available", "Available").to("committed").initial()
        .state("committed", "Committed").to("depleted").intermediate()
        .state("depleted", "Depleted").final()
    )


class InvPipelineLifecycle(Lifecycle):
    """receipt → anchored."""

    _template = (
        Lifecycle()
        .state("receipt", "Receipt").to("staging").initial()
        .state("staging", "Staging").to("anchored").intermediate()
        .state("anchored", "Anchored").final()
    )
