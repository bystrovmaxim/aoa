# packages/aoa-maxitor/src/aoa/maxitor/samples/clinical_supply/entities/cs_lifecycle.py
from aoa.action_machine.domain import Lifecycle


class ClinicalSupplyLifecycle(Lifecycle):
    """Small linear lifecycle for sample rows."""

    _template = (
        Lifecycle()
        .state("draft", "Draft").to("active").initial()
        .state("active", "Active").to("retired").intermediate()
        .state("retired", "Retired").final()
    )
