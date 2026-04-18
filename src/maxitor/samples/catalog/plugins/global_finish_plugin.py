# src/maxitor/samples/catalog/plugins/global_finish_plugin.py
from __future__ import annotations

from typing import Any

from action_machine.intents.plugins.events import GlobalFinishEvent
from action_machine.intents.plugins.on_decorator import on
from action_machine.intents.plugins.plugin import Plugin


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
