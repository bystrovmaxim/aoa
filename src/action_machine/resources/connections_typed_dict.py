# src/action_machine/resources/connections_typed_dict.py
"""
Base TypedDict contract for ``connections`` mapping passed into aspects.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``Connections`` defines a minimal static typing contract for resource managers
in action aspect signatures. The default key ``"connection"`` covers the most
common single-resource case; multi-resource actions can extend this TypedDict.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- TypedDict is static typing metadata for IDE/mypy; runtime payload is plain dict.
- ``total=False`` allows action-specific optional keys in extended contracts.
- Runtime key/type correctness is validated separately by machine checks.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    @connection declarations on action class
                 |
                 v
    Runtime builds validated connections payload (dict)
                 |
                 +--> Aspect signature typing: Connections / subclass
                 |
                 v
    Aspect reads managers by keys (e.g. connections["connection"])

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Simple case:

    @connection(PostgresConnectionManager, key="connection", description="Primary DB")
    class MyAction(BaseAction[...]):
        @regular_aspect("Load")
        async def load(self, params, state, box, connections: Connections) -> ...:
            conn = connections["connection"]
            ...

Extended case:

    class MyConnections(Connections, total=False):
        cache: BaseResourceManager
        analytics_db: BaseResourceManager

    @connection(PostgresConnectionManager, key="connection", description="Primary DB")
    @connection(RedisConnectionManager, key="cache", description="Cache")
    @connection(PostgresConnectionManager, key="analytics_db", description="Analytics DB")
    class ComplexAction(BaseAction[...]):
        @regular_aspect("Load")
        async def load(self, params, state, box, connections: MyConnections) -> ...:
            db = connections["connection"]
            cache = connections["cache"]
            ...

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- TypedDict alone does not enforce runtime resource presence.
- Key names must still match ``@connection`` declarations on action classes.
- Keep extensions action-specific to avoid global "god" contracts.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Static type contract for action resource connection payloads.
CONTRACT: Provide default key and extensible TypedDict inheritance path.
INVARIANTS: Runtime object is dict; static typing augments editor/type checks.
FLOW: class declarations -> runtime validation -> typed access in aspects.
FAILURES: Mismatched keys fail at runtime validation, not TypedDict definition.
EXTENSION POINTS: Create per-action TypedDict subclasses with additional keys.
AI-CORE-END
"""

from typing import TypedDict

from action_machine.resources.base_resource_manager import BaseResourceManager


class Connections(TypedDict, total=False):
    """
    Base TypedDict for action ``connections`` mapping.

    Includes standard ``connection`` key for common single-resource scenarios.
    """

    connection: BaseResourceManager
