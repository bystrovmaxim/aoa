# src/action_machine/core/meta_intents.py
"""
ActionMetaIntent and ResourceMetaIntent — marker mixins for the ``@meta`` decorator.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``@meta`` applies to two disjoint class hierarchies: **actions** (``BaseAction``
subclasses) and **resource managers** (``BaseResourceManager`` subclasses).
Each hierarchy carries its own empty mixin so the type **declares intent** to
participate in the meta grammar; the framework enforces a non-empty
``@meta(description=..., domain=...)`` declaration via ``issubclass`` checks
and ``validate_meta_required``.

``ActionMetaIntent`` appears in the MRO of every action. If the action declares
aspects, ``_meta_info`` must be present (set by ``@meta``) or metadata build
fails with ``TypeError``.

``ResourceMetaIntent`` appears in the MRO of every resource manager. ``@meta`` is
always required for those types.

The ``@meta`` decorator rejects targets that inherit neither mixin.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    class BaseAction[P, R](
        ABC,
        RoleIntent,
        DependencyIntent[object],
        CheckerIntent,
        AspectIntent,
        ConnectionIntent,
        ActionMetaIntent,             ← intent: @meta required (with aspects rule)
    ): ...

    class BaseResourceManager(ABC, ResourceMetaIntent):
        ...                             ← intent: @meta always required

    @meta(description="Create order", domain=OrdersDomain)
    @check_roles(ManagerRole)
    class CreateOrderAction(BaseAction[OrderParams, OrderResult]):
        ...

    @meta(description="PostgreSQL manager", domain=WarehouseDomain)
    class PostgresManager(BaseResourceManager):
        ...

    # @meta checks:
    #   issubclass(cls, ActionMetaIntent) or issubclass(cls, ResourceMetaIntent)

    # Metadata build checks (validate_meta_required):
    #   ActionMetaIntent + aspects → _meta_info required
    #   ResourceMetaIntent → _meta_info required

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

1. **Two intents, one decorator.** A single ``@meta`` serves both trees; intents
   are split because ``BaseAction`` and ``BaseResourceManager`` do not share a
   common concrete base.

2. **Markers carry no logic.** Mixins are empty; they exist only for
   ``issubclass`` in ``@meta`` and validators.

3. **Declaration obligation.** Carrying ``ActionMetaIntent`` or
   ``ResourceMetaIntent`` in MRO means the class must satisfy the corresponding
   ``@meta`` rules — not “permission to optionally decorate”, but a checked
   contract.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path — action and manager::

    @meta(description="Health ping", domain=InfraDomain)
    @check_roles(NoneRole)
    class PingAction(BaseAction[BaseParams, BaseResult]):
        @summary_aspect("Pong")
        async def pong(self, params, state, box, connections):
            return BaseResult()

    @meta(description="Redis connections", domain=CacheDomain)
    class RedisManager(BaseResourceManager):
        def get_wrapper_class(self):
            return None

Edge case — action with aspects but no ``@meta``::

    class BadAction(BaseAction[BaseParams, BaseResult]):
        @summary_aspect("Broken")
        async def broken(self, params, state, box, connections):
            return BaseResult()
    # validate_meta_required(BadAction, ...) → TypeError (missing @meta)

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- ``validate_meta_required`` raises ``TypeError`` when mandatory ``@meta`` is
  missing per the rules above.
- Mixins do not validate ``_meta_info`` shape; ``@meta`` does at apply time.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Meta-description intent markers for actions vs resource managers.
CONTRACT: Empty mixins; ``@meta`` + ``validate_meta_required`` enforce declarations.
INVARIANTS: No fields on mixins; graph facet key ``meta`` unchanged.
FLOW: decorator writes ``_meta_info`` → ``MetaIntentInspector`` → coordinator graph.
FAILURES: ``TypeError`` from decorator or ``validate_meta_required``.
EXTENSION POINTS: Domains and descriptions only; facet wiring is inspector-side.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from typing import Any, ClassVar


class ActionMetaIntent:
    """
    Intent marker: action types participate in the ``@meta`` grammar.

    ``BaseAction`` includes this mixin. Subclasses must follow ``@meta`` rules
    enforced by the decorator and ``validate_meta_required``. ``@meta`` sets
    ``_meta_info`` with ``description`` and ``domain``.
    """

    _meta_info: ClassVar[dict[str, Any]]


class ResourceMetaIntent:
    """
    Intent marker: resource manager types always require ``@meta``.

    ``BaseResourceManager`` includes this mixin. Every concrete manager must
    apply ``@meta`` so ``_meta_info`` exists before metadata build.
    """

    _meta_info: ClassVar[dict[str, Any]]


def validate_meta_required(
    cls: type,
    has_meta_info: bool,
    aspects: list[Any],
) -> None:
    """
    Enforce ``ActionMetaIntent`` / ``ResourceMetaIntent`` obligations for ``@meta``.

    No-op when ``has_meta_info`` is true. Otherwise raises ``TypeError`` when an
    action with aspects or any resource manager is missing ``@meta``.
    """
    if has_meta_info:
        return

    if issubclass(cls, ActionMetaIntent) and aspects:
        raise TypeError(
            f"Action {cls.__name__} is missing @meta. "
            f"Add @meta(description=..., domain=...) before the class body."
        )
    if issubclass(cls, ResourceMetaIntent):
        raise TypeError(
            f"Resource manager {cls.__name__} is missing @meta. "
            f"Add @meta(description=..., domain=...) before the class body."
        )
