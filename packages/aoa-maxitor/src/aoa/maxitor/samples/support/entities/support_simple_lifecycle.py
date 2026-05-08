# packages/aoa-maxitor/src/aoa/maxitor/samples/support/entities/support_simple_lifecycle.py
"""Minimal lifecycle for sparse support-graph demo."""

from aoa.action_machine.domain import Lifecycle


class SupportSparseLifecycle(Lifecycle):
    """intake → working → done."""

    _template = (
        Lifecycle()
        .state("intake", "Intake").to("working").initial()
        .state("working", "Working").to("done").intermediate()
        .state("done", "Done").final()
    )
