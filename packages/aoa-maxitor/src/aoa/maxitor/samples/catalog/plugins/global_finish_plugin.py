# packages/aoa-maxitor/src/aoa/maxitor/samples/catalog/plugins/global_finish_plugin.py
from __future__ import annotations

from typing import Any

from aoa.action_machine.intents.on import GlobalFinishEvent, on
from aoa.action_machine.plugin import Plugin


class CatalogGlobalFinishPlugin(Plugin):
    async def get_initial_state(self) -> dict[str, Any]:
        return {}

    @on(GlobalFinishEvent, action_name_pattern=r".*")
    async def on_any_finish(
        self,
        state: Any,
        event: GlobalFinishEvent,
        log: Any,
    ) -> Any:
        return state
