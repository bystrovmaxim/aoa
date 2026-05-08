# packages/aoa-maxitor/src/aoa/maxitor/samples/assurance_portfolio/entities/ap_lifecycle.py
from aoa.action_machine.domain import Lifecycle


class AssurancePortfolioLifecycle(Lifecycle):
    """Linear bookkeeping lifecycle for seeded portfolio rows."""

    _template = (
        Lifecycle()
        .state("intake", "Intake").to("steady").initial()
        .state("steady", "Steady").to("frozen").intermediate()
        .state("frozen", "Frozen").final()
    )
