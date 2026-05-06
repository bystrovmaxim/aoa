# src/maxitor/samples/messaging/plugins/after_send_plugin.py
from __future__ import annotations

from typing import Any

from action_machine.intents.on import AfterRegularAspectEvent, on
from action_machine.plugin import Plugin


class MessagingAfterSendPlugin(Plugin):
    async def get_initial_state(self) -> dict[str, Any]:
        return {}

    @on(
        AfterRegularAspectEvent,
        action_name_pattern=r".*PublishTransactionalOutbox.*",
        aspect_name_pattern=r".*dispatch.*",
    )
    async def on_after_dispatch(
        self,
        state: Any,
        event: AfterRegularAspectEvent,
        log: Any,
    ) -> Any:
        return state
