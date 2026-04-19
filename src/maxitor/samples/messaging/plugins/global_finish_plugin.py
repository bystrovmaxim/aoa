# src/maxitor/samples/messaging/plugins/global_finish_plugin.py
from __future__ import annotations

from typing import Any

from action_machine.plugin.events import GlobalFinishEvent
from action_machine.intents.on.on_decorator import on
from action_machine.plugin.plugin import Plugin


class MessagingGlobalFinishPlugin(Plugin):
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
