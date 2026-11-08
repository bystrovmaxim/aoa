"""A storage that is not PostgreSQL takes no pool.

``pool=`` and ``connection_params=`` belong to a PostgreSQL storage. A storage of another kind
knows no pool, and giving it one is refused when it is built.

Run: uv run python examples/extensions/postgresql/17_other_kind.py
"""

from aoa.action_machine.intents.entities import entities
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources import BaseStorage
from aoa.action_machine.resources.postgres import PostgresPool


@meta(description="An in-memory cache of the shop")
@entities()
class ShopCacheStorage(BaseStorage):
    """Keeps its data in memory; there is no pool to take."""

    @classmethod
    def get_wrapper_class(cls) -> None:
        """No wrapper: nothing to protect."""
        return None


# Run the case.
for arguments in ({"pool": PostgresPool(pool=object())}, {"connection_params": "postgresql://example.invalid/shop"}):
    try:
        ShopCacheStorage(**arguments)
    except TypeError as error:
        print(f"{sorted(arguments)[0]}= refused with {type(error).__name__}")
    else:
        raise AssertionError("A pool was given to a storage that knows none")
