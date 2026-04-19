# src/maxitor/samples/store/plugins/unhandled_error_plugin.py
from __future__ import annotations

from typing import Any

from action_machine.plugin.events import UnhandledErrorEvent
from action_machine.intents.on.on_decorator import on
from action_machine.plugin.plugin import Plugin


class UnhandledErrorSwallowPlugin(Plugin):
    """Поглощает ``UnhandledErrorEvent`` в демо (отдельно от графа подписок)."""

    async def get_initial_state(self) -> dict[str, Any]:
        return {}

    @on(UnhandledErrorEvent, action_name_pattern=r".*", ignore_exceptions=True)
    async def on_swallow_errors(
        self,
        state: Any,
        event: UnhandledErrorEvent,
        log: Any,
    ) -> Any:
        return state
