"""A PostgreSQL storage needs a way to reach its database.

Built with neither a pool nor connection parameters, a PostgreSQL storage is refused when it
is built, before ``open`` and before any database access.

Run: uv run python examples/extensions/postgresql/10_no_source.py
"""

import asyncio

from aoa.action_machine.exceptions import ConnectionValidationError
from aoa.action_machine.resources.postgres import PostgresStorage


async def main():
    """Run this case and verify its observable result."""
    try:
        PostgresStorage()
    except ConnectionValidationError as error:
        print(type(error).__name__, "needs exactly one of pool and connection_params")
    else:
        raise AssertionError("A resource without a connection source was accepted")


if __name__ == "__main__":
    asyncio.run(main())
