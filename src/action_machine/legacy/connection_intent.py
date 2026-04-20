# src/action_machine/legacy/connection_intent.py
"""
ConnectionIntent marker mixin for ``@connection`` decorator.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``ConnectionIntent`` is a marker mixin that allows ``@connection`` usage on a
class. During decorator application, runtime checks:

    if not issubclass(cls, ConnectionIntent):
        raise TypeError("Class must inherit ConnectionIntent")

Without ``ConnectionIntent`` inheritance, ``@connection`` raises ``TypeError``.
This protects against accidental resource declarations on unsupported classes.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    class BaseAction[P, R](
        ABC,
        CheckRolesIntent,
        DependencyIntent[object],
        CheckerIntent,
        AspectIntent,
        ConnectionIntent,             <- marker: enables @connection
    ): ...

    @connection(PostgresManager, key="db", description="Primary DB")
    @connection(RedisManager, key="cache", description="Cache")
    class DataAction(BaseAction[P, R]):
        ...

    # @connection validation:
    #   1. issubclass(DataAction, ConnectionIntent) -> True -> OK
    #   2. issubclass(PostgresManager, BaseResourceManager) -> True -> OK
    #   3. key="db" is non-empty string -> OK
    #   4. Key duplicates are absent -> OK
    #   5. Writes ConnectionInfo into cls._connection_info

    # ConnectionIntentInspector reads cls._connection_info at build time.

    # ActionProductMachine validates runtime keys against connections facet.

"""

from typing import Any, ClassVar


class ConnectionIntent:
    """
    Marker mixin that enables ``@connection`` decorator usage.

    Classes that do not inherit ``ConnectionIntent`` are rejected by
    ``@connection`` at declaration time.
    """

    # Typing hint for dynamically injected class-level metadata
    _connection_info: ClassVar[list[Any]]
