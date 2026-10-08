"""A role condition must declare its refusal reason."""

from __future__ import annotations

import asyncio

from aoa.action_machine.auth import ApplicationRole
from aoa.action_machine.intents.check_roles import grant

# %% Setup


class ManagerRole(ApplicationRole):
    """Permit order management."""

    name = "manager"
    description = "Can manage orders"


# %% Run


async def main() -> None:
    """A role condition must declare its refusal reason."""
    try:
        grant(ManagerRole, when=lambda user: False)
    except ValueError as exc:
        print(type(exc).__name__ + ":", exc)


if __name__ == "__main__":
    asyncio.run(main())
