# packages/aoa-maxitor/src/aoa/maxitor/samples/store/plugins/after_charge_plugin.py
from __future__ import annotations

from typing import Any

from aoa.action_machine.intents.on import AfterRegularAspectEvent, on
from aoa.action_machine.plugin import Plugin


class AfterChargeAspectPlugin(Plugin):
    async def get_initial_state(self) -> dict[str, Any]:
        return {}

    @on(
        AfterRegularAspectEvent,
        action_name_pattern=r".*CheckoutSubmit.*",
        aspect_name_pattern=r".*charge.*",
    )
    async def on_after_charge_aspect(
        self,
        state: Any,
        event: AfterRegularAspectEvent,
        log: Any,
    ) -> Any:
        return state
