"""An object check requires a description."""

from __future__ import annotations

import asyncio

from aoa.action_machine.intents.access_decide import access_decide

# %% Setup


# %% Run


async def main() -> None:
    """An object check requires a description."""
    try:
        access_decide("")
    except ValueError as exc:
        print(type(exc).__name__ + ":", exc)


if __name__ == "__main__":
    asyncio.run(main())
