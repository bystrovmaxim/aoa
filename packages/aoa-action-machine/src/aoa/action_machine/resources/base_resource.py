# packages/aoa-action-machine/src/aoa/action_machine/resources/base_resource.py
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
This is enforced through ``MetaIntent`` in ``BaseResource``
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
``check_rollup_support()`` for each ``BaseResource`` instance and fails
fast on unsupported resources.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    class BaseResource(ABC, MetaIntent, DependsEligible):
        check_rollup_support() → raises RollupNotSupportedError
        get_wrapper_class()    → type | None

    class SqlResource(BaseResource):
        check_rollup_support() → True  (overrides, supports rollup)
        __init__(rollup=False)         (accepts rollup flag)
        commit()                       (with rollup=True -> rollback instead of commit)

    @meta(description="PostgreSQL manager", domain=WarehouseDomain)
    class PostgresResource(SqlResource):
        __init__(params, rollup=False) (passes rollup to super)

    @meta(description="Redis cache manager", domain=CacheDomain)
    class RedisManager(BaseResource):
        check_rollup_support()         (not overridden -> RollupNotSupportedError)

"""

from abc import ABC, abstractmethod
from typing import Any, Generic

from aoa.action_machine.exceptions.data_source_declaration_error import DataSourceDeclarationError
from aoa.action_machine.exceptions.rollup_not_supported_error import RollupNotSupportedError
from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.intents.depends.depends_eligible import DependsEligible
from aoa.action_machine.intents.meta.meta_intent import MetaIntent
from aoa.action_machine.resources.base_data_source import BaseDataSource, TDataSource_co
from aoa.action_machine.resources.data_source_resolver import check_data_source_arguments, resolve_data_source


@exclude_graph_model
class BaseResource(ABC, MetaIntent, DependsEligible, Generic[TDataSource_co]):
    """
    AI-CORE-BEGIN
        ROLE: Root of all managed long-lived dependencies.
        CONTRACT: Injected via DI; lives longer than a single call. May name one data source as its type argument (``TDataSource_co``).
        INVARIANTS: Three subtypes separated by lifecycle ownership; at most one data source, of the kind its base needs.
    AI-CORE-END

    Base abstract contract for all resource manager implementations.

    A resource may name the data source it shares with other resources as the type
    argument of its base — ``class OrdersResource(PostgresResource[ShopDataSource])`` —
    and gets an instance of it when it is built. A resource that stores an entity names one;
    a resource that stores nothing may name none.
    """

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Refuse a data source of the wrong kind, and a second data source, when the class is created."""
        super().__init_subclass__(**kwargs)
        check_data_source_arguments(cls)

    @classmethod
    def data_source_type(cls) -> type[BaseDataSource] | None:
        """Return the data source this resource names, or ``None`` when it works on its own."""
        return resolve_data_source(cls)

    @classmethod
    def _check_data_source(cls, data_source: BaseDataSource | None) -> None:
        """
        Refuse a data source this resource does not name, or the absence of the one it does.

        Raises:
            DataSourceDeclarationError: naming the resource, the class it declares and what was given.
        """
        declared = cls.data_source_type()
        if declared is None and data_source is not None:
            raise DataSourceDeclarationError(
                f"{cls.__name__} names no data source, so it takes none; got {type(data_source).__name__}."
            )
        if declared is not None and not isinstance(data_source, declared):
            given = "none" if data_source is None else type(data_source).__name__
            raise DataSourceDeclarationError(f"{cls.__name__} works through {declared.__name__}: pass data_source= of that class; got {given}.")

    async def check_rollup_support(self) -> bool:
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
    def get_wrapper_class(self) -> type["BaseResource"] | None:
        """
        Return wrapper (proxy) class for nested action propagation.

        Return ``None`` when direct pass-through is safe for this manager.
        """
        pass
