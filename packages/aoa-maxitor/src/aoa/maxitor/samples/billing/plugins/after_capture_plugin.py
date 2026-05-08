# packages/aoa-maxitor/src/aoa/maxitor/samples/billing/plugins/after_capture_plugin.py
from __future__ import annotations

from typing import Any

from aoa.action_machine.intents.on import AfterRegularAspectEvent, on
from aoa.action_machine.plugin import Plugin


class BillingAfterCapturePlugin(Plugin):
    async def get_initial_state(self) -> dict[str, Any]:
        return {}

    @on(
        AfterRegularAspectEvent,
        action_name_pattern=r".*InvoiceSettle.*",
        aspect_name_pattern=r".*capture.*",
    )
    async def on_after_capture(
        self,
        state: Any,
        event: AfterRegularAspectEvent,
        log: Any,
    ) -> Any:
        return state
