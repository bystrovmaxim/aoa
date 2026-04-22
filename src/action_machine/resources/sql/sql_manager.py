# src/action_machine/resources/sql/sql_manager.py
"""
Transactional SQL manager interface.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``SqlManager`` is an abstract base class for transactional SQL connection
managers. It defines the contract:
``open()``, ``begin()``, ``commit()``, ``rollback()``, ``execute()``.

By inheriting ``BaseResourceManager`` it keeps metadata/wrapper contracts and
rollup capability checks aligned with the resource subsystem.

═══════════════════════════════════════════════════════════════════════════════
ROLLUP SUPPORT
═══════════════════════════════════════════════════════════════════════════════

``SqlManager`` supports rollup mode natively. Constructor stores ``rollup``
flag in ``self._rollup``.

When ``rollup=True``, ``commit()`` calls ``rollback()`` instead of a real
commit. For deterministic rollback semantics, callers should use explicit
transaction scope: ``open()`` -> ``begin()`` -> mutate -> ``commit()``.

``check_rollup_support()`` always returns ``True``, so all descendants are
considered rollup-capable unless they break contract intentionally.

═══════════════════════════════════════════════════════════════════════════════
ROLLUP PROPERTY RESILIENCE
═══════════════════════════════════════════════════════════════════════════════

``rollup`` property uses ``getattr(self, "_rollup", False)`` instead of direct
attribute access. This keeps behavior stable even for test doubles that do not
call ``super().__init__()``. In such cases, default is safely ``False``.

═══════════════════════════════════════════════════════════════════════════════
ROLLUP LIFECYCLE
═══════════════════════════════════════════════════════════════════════════════

    # Caller creates manager with rollup=True:
    db = PostgresConnectionManager(params, rollup=True)

    # Aspect code runs as usual:
    await db.open()
    await db.begin()                   # -> one transaction for all execute calls
    await db.execute("INSERT ...")
    await db.execute("UPDATE ...")
    await db.commit()                  # -> ROLLBACK (instead of COMMIT)

    # All changes are rolled back, production data is untouched.

═══════════════════════════════════════════════════════════════════════════════
ROLLUP PROPAGATION TO CHILD ACTIONS
═══════════════════════════════════════════════════════════════════════════════

``WrapperSqlManager`` exposes ``rollup`` by delegating to the wrapped manager.
Child actions receive consistent rollup visibility without storing a separate
flag on the proxy.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    BaseResourceManager (ABC)
        │
        └── SqlManager (ABC)
                │   _rollup: bool
                │   check_rollup_support() → True
                │   commit() → rollback() when _rollup=True
                │
                ├── PostgresConnectionManager
                │       __init__(params, rollup=False)
                │       begin() → transaction start (root action)
                │
                └── WrapperSqlManager (proxy)
                        __init__(connection_manager)
                        rollup read from inner (delegation)
                        begin/open/commit/rollback prohibited

"""

from abc import abstractmethod
from typing import Any

from action_machine.resources.base_resource_manager import BaseResourceManager
from action_machine.resources.sql.protocol_sql_manager import ProtocolSqlManager
from action_machine.resources.sql.wrapper_sql_manager import WrapperSqlManager


class SqlManager(BaseResourceManager, ProtocolSqlManager):
    """
    Base class for transaction-capable SQL connection managers.
    """

    def __init__(self, rollup: bool = False) -> None:
        """Initialize manager with optional rollup mode."""
        self._rollup: bool = rollup

    @property
    def rollup(self) -> bool:
        """Return current rollup flag with safe fallback for test doubles."""
        return getattr(self, "_rollup", False)

    def check_rollup_support(self) -> bool:
        """Confirm rollup support for this manager type."""
        return True

    def get_wrapper_class(self) -> type[BaseResourceManager] | None:
        """Return proxy class that blocks nested transaction control."""
        return WrapperSqlManager

    @abstractmethod
    async def open(self) -> None:
        """Open underlying resource connection."""
        pass

    @abstractmethod
    async def begin(self) -> None:
        """Start transaction scope."""
        pass

    async def commit(self) -> None:
        """
        Commit transaction or rollback when rollup mode is enabled.
        """
        if self.rollup:
            await self.rollback()
            return

    @abstractmethod
    async def rollback(self) -> None:
        """Rollback active transaction."""
        pass

    @abstractmethod
    async def execute(self, query: str, params: tuple[Any, ...] | None = None) -> Any:
        """
        Execute query against underlying resource.
        """
        pass
