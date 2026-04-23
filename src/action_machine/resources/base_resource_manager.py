# src/action_machine/resources/base_resource_manager.py
"""
Base abstract class for all resource managers.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A resource manager is any object that controls an external resource
(database connection, cache, queue, and so on) and is passed into action
aspects through the ``connections`` mapping.

Each resource manager must provide a wrapper class used when the resource is
propagated to child actions. The wrapper blocks lifecycle control
(``open/begin/commit/rollback``) but allows execution operations.

═══════════════════════════════════════════════════════════════════════════════
REQUIRED @meta DECORATOR
═══════════════════════════════════════════════════════════════════════════════

Every resource manager must declare ``@meta(...)`` with description/domain.
This is enforced through ``ResourceMetaIntent`` in ``BaseResourceManager``
inheritance and validated during metadata build.

═══════════════════════════════════════════════════════════════════════════════
ROLLUP SUPPORT
═══════════════════════════════════════════════════════════════════════════════

Rollup mode enables safe execution against production-like data: writes run in
transaction scope, but commit stage performs rollback instead of persist.

``check_rollup_support()`` defines whether the concrete manager supports rollup.
Default implementation raises ``RollupNotSupportedError``. Managers that support
rollup (for example SQL managers) override the method.

When ``DependencyFactory.resolve(..., rollup=True)`` builds managers, it calls
``check_rollup_support()`` for each ``BaseResourceManager`` instance and fails
fast on unsupported resources.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    class BaseResourceManager(ABC, ResourceMetaIntent):
        check_rollup_support() → raises RollupNotSupportedError
        get_wrapper_class()    → type | None

    class SqlManager(BaseResourceManager):
        check_rollup_support() → True  (overrides, supports rollup)
        __init__(rollup=False)         (accepts rollup flag)
        commit()                       (with rollup=True -> rollback instead of commit)

    @meta(description="PostgreSQL manager", domain=WarehouseDomain)
    class PostgresConnectionManager(SqlManager):
        __init__(params, rollup=False) (passes rollup to super)

    @meta(description="Redis cache manager", domain=CacheDomain)
    class RedisManager(BaseResourceManager):
        check_rollup_support()         (not overridden -> RollupNotSupportedError)

"""

from abc import ABC, abstractmethod

from action_machine.exceptions import RollupNotSupportedError
from action_machine.intents.meta.resource_meta_intent import ResourceMetaIntent


class BaseResourceManager(ABC, ResourceMetaIntent):
    """
    Base abstract contract for all resource manager implementations.
    """

    def check_rollup_support(self) -> bool:
        """
        Check whether this manager supports rollup transaction mode.

        Default behavior raises ``RollupNotSupportedError``; rollup-capable
        managers override and return ``True``.
        """
        raise RollupNotSupportedError(
            f"Class '{type(self).__name__}' does not support rollup. "
            f"Implement check_rollup_support() or use a resource manager "
            f"that supports transactional rollback."
        )

    @abstractmethod
    def get_wrapper_class(self) -> type["BaseResourceManager"] | None:
        """
        Return wrapper (proxy) class for nested action propagation.

        Return ``None`` when direct pass-through is safe for this manager.
        """
        pass
