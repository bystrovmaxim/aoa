"""A pool holder reports missing startup.

The holder must give a useful error if a factory reaches it before application startup.

Run: uv run python examples/step_17_connections/17_holder_before_startup.py
"""

import asyncio


class PoolHolder:
    """Expose a pool after service startup."""
    pool = None
    def require(self):
        """Reject use before startup or after shutdown."""
        if self.pool is None:
            raise RuntimeError("Pool is not started")
        return self.pool


async def main():
    """Run this case and verify its observable result."""
    try:
        PoolHolder().require()
    except RuntimeError as error:
        assert str(error) == "Pool is not started"
        print(str(error))
    else:
        raise AssertionError("An empty holder returned a pool")


if __name__ == "__main__":
    asyncio.run(main())
