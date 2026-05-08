# packages/aoa-maxitor/src/aoa/maxitor/samples/billing/entities/billing_dense_lifecycle.py
"""Tiny lifecycles for expanded billing ER demo rows."""

from aoa.action_machine.domain import Lifecycle


class BillingDenseLifecycle(Lifecycle):
    """open → finalized (single terminal)."""

    _template = Lifecycle().state("open", "Open").to("finalized").initial().state("finalized", "Finalized").final()


class BillingPipelineLifecycle(Lifecycle):
    """staged ingest pipeline markers."""

    _template = (
        Lifecycle()
        .state("staged", "Staged")
        .to("validated")
        .initial()
        .state("validated", "Validated")
        .to("exported")
        .intermediate()
        .state("exported", "Exported")
        .final()
    )
