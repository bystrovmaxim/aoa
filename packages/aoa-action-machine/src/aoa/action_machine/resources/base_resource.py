# packages/aoa-action-machine/src/aoa/action_machine/resources/base_resource.py
"""
BaseResource — declaration contract for managed resources.

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

    class SqlStorage(BaseStorage):
        check_rollup_support() → True  (overrides, supports rollup)
        __init__(rollup=False)         (accepts rollup flag)
        commit()                       (with rollup=True -> rollback instead of commit)

    @meta(description="PostgreSQL manager", domain=WarehouseDomain)
    class PostgresStorage(SqlStorage):
        __init__(params, rollup=False) (passes rollup to super)

    @meta(description="Redis cache manager", domain=CacheDomain)
    class RedisStorage(BaseStorage):
        check_rollup_support()         (not overridden -> RollupNotSupportedError)

"""

from abc import ABC, abstractmethod
from typing import Any, Generic

from aoa.action_machine.exceptions.data_source_declaration_error import DataSourceDeclarationError
from aoa.action_machine.exceptions.declaration_structure_error import DeclarationStructureError
from aoa.action_machine.exceptions.naming_suffix_error import NamingSuffixError
from aoa.action_machine.exceptions.rollup_not_supported_error import RollupNotSupportedError
from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.intents.depends.depends_eligible import DependsEligible
from aoa.action_machine.intents.meta.meta_intent import MetaIntent
from aoa.action_machine.resources.base_data_source import BaseDataSource, TDataSource_co
from aoa.action_machine.resources.data_source_resolver import check_data_source_arguments, resolve_data_source


@exclude_graph_model
class BaseResource(ABC, MetaIntent, DependsEligible, Generic[TDataSource_co]):
    """
    A managed resource belongs to one kind and declares its wrapper without an instance.

    AI-CORE-BEGIN
    ROLE: Root of managed long-lived dependencies.
    CONTRACT: Concrete resources inherit a canonical kind and declare wrappers through a class method.
    INVARIANTS: Exactly one ancestry-derived kind; at most one compatible data source.
    AI-CORE-END
    """

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Validate resource kind, name and data source declarations."""
        super().__init_subclass__(**kwargs)
        _check_resource_kind(cls)
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

    @classmethod
    @abstractmethod
    def get_wrapper_class(cls) -> type["BaseResource"] | None:
        """Return a wrapper class, or ``None`` for direct pass-through."""
        pass


_KIND_BASES = "BaseStorage, BaseGateway or BaseController"
_KIND_DECLARATIONS = {
    ("aoa.action_machine.resources.base_storage", "BaseStorage"): "Storage",
    ("aoa.action_machine.resources.base_gateway", "BaseGateway"): "Gateway",
    ("aoa.action_machine.resources.base_controller", "BaseController"): "Controller",
}
_KIND_TYPES: dict[type, str] = {}


def resource_kind(cls: type) -> str:
    """
    Return the resource kind established by framework ancestry.

    AI-CORE-BEGIN
    ROLE: Resolve a resource's canonical kind.
    CONTRACT: Return Storage, Gateway or Controller from registered base identities.
    INVARIANTS: Descendant attributes cannot change kind; mixed kinds are refused.
    AI-CORE-END
    """
    kinds = {_KIND_TYPES[base] for base in cls.__mro__ if base in _KIND_TYPES}
    if len(kinds) != 1:
        raise DeclarationStructureError(
            f"Class '{cls.__name__}' inherits {len(kinds)} resource kinds: a resource inherits exactly one of {_KIND_BASES}."
        )
    return next(iter(kinds))


def _check_resource_kind(cls: type) -> None:
    """Admit canonical kind bases and validate every descendant's name."""
    if BaseResource in cls.__bases__:
        declaration = (cls.__module__, cls.__qualname__)
        kind = _KIND_DECLARATIONS.get(declaration)
        # Each canonical declaration registers once during framework import.
        if kind is not None and kind not in _KIND_TYPES.values():
            _KIND_TYPES[cls] = kind
            return
        raise DeclarationStructureError(
            f"Class '{cls.__name__}' inherits BaseResource directly. "
            f"A resource inherits one of the three kind base classes instead: {_KIND_BASES}."
        )
    kind = resource_kind(cls)
    name = cls.__name__
    if name.endswith("Wrapper"):
        if not name.endswith(f"{kind}Wrapper"):
            raise NamingSuffixError(
                f"Class '{name}' is a wrapper of a Base{kind} and lacks the '{kind}Wrapper' suffix. "
                f"Rename to '{name.removesuffix('Wrapper')}{kind}Wrapper'."
            )
    elif not name.endswith(kind):
        raise NamingSuffixError(f"Class '{name}' inherits Base{kind} but lacks the '{kind}' suffix. Rename to '{name}{kind}'.")
