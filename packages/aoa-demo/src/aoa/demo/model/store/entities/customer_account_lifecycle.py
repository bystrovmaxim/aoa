# packages/aoa-demo/src/aoa/demo/model/store/entities/customer_account_lifecycle.py
"""Customer account lifecycle demo."""

from __future__ import annotations

from aoa.action_machine.domain import Lifecycle


class CustomerAccountLifecycle(Lifecycle):
    """Three states: provisioned → active → closed."""

    _template = (
        Lifecycle()
        .state("provisioned", "Provisioned")
        .to("active")
        .initial()
        .state("active", "Active")
        .to("closed")
        .intermediate()
        .state("closed", "Closed")
        .final()
    )
