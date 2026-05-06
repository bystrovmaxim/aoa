# src/maxitor/samples/store/plugins/unhandled_error_plugin.py
from __future__ import annotations

from typing import Any

from action_machine.intents.on import UnhandledErrorEvent, on
from action_machine.plugin import Plugin


class UnhandledErrorSwallowPlugin(Plugin):
    """Swallows ``UnhandledErrorEvent`` in the demo (separate from the subscription graph)."""

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
