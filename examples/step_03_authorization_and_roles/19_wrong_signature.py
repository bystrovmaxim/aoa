"""An object check does not receive pipeline state."""

from __future__ import annotations

import asyncio

from aoa.action_machine.intents.access_control import Allowed, Verdict
from aoa.action_machine.intents.access_decide import access_decide
from aoa.action_machine.model import BaseParams
from aoa.action_machine.resources import BaseResource
from aoa.action_machine.runtime.tools_box import ToolsBox

# %% Setup


# %% Run


async def main() -> None:
    """An object check does not receive pipeline state."""
    try:

        @access_decide("Check the order")
        async def order_access_decide(
            self, params: BaseParams, state: object, box: ToolsBox, connections: dict[str, BaseResource]
        ) -> Verdict:
            """Demonstrate the extra state argument."""
            return Allowed()
    except TypeError as exc:
        print(type(exc).__name__ + ":", exc)


if __name__ == "__main__":
    asyncio.run(main())
