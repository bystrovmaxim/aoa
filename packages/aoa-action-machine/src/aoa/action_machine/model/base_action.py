# packages/aoa-action-machine/src/aoa/action_machine/model/base_action.py
"""
Abstract base class for every ActionMachine action (user-defined command).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``BaseAction`` is parameterized by ``P`` (a ``BaseParams`` subclass) and ``R``
(a ``BaseResult`` subclass). Subclasses declare behavior with class- and method-level decorators;
markers in the MRO enable those decorators. Runtime execution and metadata reads use
interchange graph-node payloads assembled when ``NodeGraphCoordinator.build()`` runs the
graph-model inspectors—not through helper APIs on this class.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    Decorators (import time)
         │
         ▼
    Class-level / method-level scratch attrs on the action class
         │
         ▼
    NodeGraphCoordinator.build()  →  inspectors  →  interchange snapshots + graph edges
         │
         ▼
    ActionProductMachine.run()  →  get_snapshot(action_cls, snapshot_key)

═══════════════════════════════════════════════════════════════════════════════
CACHING
═══════════════════════════════════════════════════════════════════════════════

Caching is **opt-in** for the whole machine: pass a
:class:`~aoa.action_machine.runtime.cache_coordinator.CacheCoordinator` into
:class:`~aoa.action_machine.runtime.action_product_machine.ActionProductMachine`
(``cache_coordinator=...``). When it is ``None`` (default), the engine calls no
cache declaration.

The coordinator lives on the **machine instance**, not on ``BaseAction``. Do **not**
use a ``ClassVar`` (or similar) on the action class to hold a cache or coordinator;
that pattern is out of scope for v1.

**v1 does not implement single-flight (de-duplication of in-flight runs).** Parallel
callers with the same key may each run the pipeline until entries exist.

An action says what it caches with four declarations (``intents/cache``), each an
``async`` method with a description, a suffix and a fixed signature, at most one of
each kind and never inherited:

- ``@cache_key`` — ``…_cache_key(self, params, box, connections) -> str | None``; ``None``
  skips the cache for this call. For data scoped to a **subject** (for example a tenant),
  the key **must** include that scope; ``@context_requires`` gives it to the key.
- ``@cache_read`` — ``…_cache_read(self, params, box, connections, entry) -> Result | None``;
  ``None`` treats the entry as stale (the machine drops it and runs the pipeline). Without
  it, a hit returns the stored Result.
- ``@cache_write`` — ``…_cache_write(self, params, box, connections, result, duration_ms)
  -> list[CacheTag] | None``; ``None`` skips the write. Called only when the key was not
  ``None`` and the pipeline finished cleanly.
- ``@cache_invalidate`` — ``…_cache_invalidate(self, params, box, connections, result)
  -> list[CacheTag] | None``; the tags of the entries to drop, called after every clean
  pipeline, **before** the write, so the action's own fresh entry is never dropped by it.

A method under an old hook name (``cache_key``, ``read_cache``, ``on_cache_write``,
``on_cache_invalidate``) is refused when the class is created: the machine no longer
calls it.

Results produced only via a matching ``@on_error`` handler (**handled error path**)
are **not** written to the cache and do not trigger ``@cache_invalidate``.

If a cache declaration, validation of its return value, or a coordinator method raises,
the exception propagates to the caller. In v1 the machine does **not** emit
``GlobalFinishEvent`` when that happens after ``GlobalStartEvent`` (same class of
lifecycle gap as an unhandled pipeline error). :exc:`CacheContractError` is raised
when a declaration's return value violates the typed contract (for example wrong type or
empty ``cache_key`` string).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE — MARKER MIXINS
═══════════════════════════════════════════════════════════════════════════════

``BaseAction`` inherits marker mixins only (no inspector logic):

    MetaIntent             → ``@meta`` (required)
    CheckRolesIntent             → ``@check_roles``
    DependsEligible      → nominal types allowed as ``@depends`` targets
    DependsIntent        → ``@depends`` (bound ``DependsEligible``)
    CheckerIntent          → result / field checkers on aspect methods
    AspectIntent           → ``@regular_aspect`` / ``@summary_aspect``
    CompensateIntent       → ``@compensate``
    ConnectionIntent       → ``@connection``
    OnErrorIntent          → ``@on_error``
    ContextRequiresIntent  → ``@context_requires``
    SensitiveIntent        → ``@sensitive`` (property masking; graph via resolver)

Class-level decorators validate the marker immediately; method-level decorators
are validated when the coordinator runs inspectors on the class.

Params / result bindings appear on interchange ``Action`` rows via
``ParamsGraphEdge`` / ``ResultGraphEdge`` (:class:`~aoa.action_machine.graph.nodes.action_graph_node.ActionGraphNode`).

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path::

    @meta(description="Ping", domain=SystemDomain)
    @check_roles(GuestRole)
    class PingAction(BaseAction[BaseParams, BaseResult]):
        @summary_aspect("Pong")
        async def pong_summary(self, params, state, box, connections):
            return BaseResult()

Edge case: ``class Bad(BaseAction[BaseParams, BaseResult]):`` (name not ending in
``"Action"``) raises ``NamingSuffixError`` in ``__init_subclass__``.
"""

from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING, Any

from aoa.action_machine.exceptions.naming_suffix_error import NamingSuffixError
from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.intents.access_decide.access_decide_intent import AccessDecideIntent
from aoa.action_machine.intents.aspects.aspect_intent import AspectIntent
from aoa.action_machine.intents.cache.cache_intent import CacheIntent
from aoa.action_machine.intents.cache.cache_intent_resolver import validate_cache_declarations
from aoa.action_machine.intents.check_roles.check_roles_intent import CheckRolesIntent
from aoa.action_machine.intents.checkers.checker_intent import CheckerIntent
from aoa.action_machine.intents.compensate.compensate_intent import CompensateIntent
from aoa.action_machine.intents.connection.connection_intent import ConnectionIntent
from aoa.action_machine.intents.context_requires.context_requires_intent import ContextRequiresIntent
from aoa.action_machine.intents.depends.depends_eligible import DependsEligible
from aoa.action_machine.intents.depends.depends_intent import DependsIntent
from aoa.action_machine.intents.meta.meta_intent import MetaIntent
from aoa.action_machine.intents.on_error.on_error_intent import OnErrorIntent
from aoa.action_machine.intents.sensitive.sensitive_intent import SensitiveIntent
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.model.base_result import BaseResult
from aoa.action_machine.system_core.type_introspection import TypeIntrospection

if TYPE_CHECKING:
    # Deferred: runtime.tools_box imports BaseAction at module level, so a top-level
    # import here would cycle. ToolsBox is only ever used as a type annotation below.

    # Deferred: context.context's own imports don't touch base_action directly, but
    # model/__init__.py eagerly imports base_action — so context.context (imported
    # first, e.g. by aoa-otel/aoa-fastapi-adapter/aoa-mcp-adapter before anything
    # touches `model`) -> context.request_info -> model.base_schema -> triggers
    # model/__init__.py -> base_action -> context.context (still mid-import) is a
    # real transitive cycle. Context is only ever used as a type annotation below.
    pass

_REQUIRED_SUFFIX = "Action"


@exclude_graph_model
class BaseAction[P: BaseParams, R: BaseResult](
    ABC,
    MetaIntent,
    CheckRolesIntent,
    DependsEligible,
    DependsIntent[DependsEligible],
    CheckerIntent,
    AspectIntent,
    AccessDecideIntent,
    CacheIntent,
    CompensateIntent,
    ConnectionIntent,
    OnErrorIntent,
    ContextRequiresIntent,
    SensitiveIntent,
):
    """
    AI-CORE-BEGIN
    ROLE: Unit of business work: Params → Result.
    CONTRACT: Everything external via ``@depends``/``@connection``.
    INVARIANTS: Knows nothing about transport, coordinators, or storage.
    CACHE: Optional ``@cache_key`` / ``@cache_read`` / ``@cache_write`` / ``@cache_invalidate`` declarations in the class's own body, at most one of each kind, never inherited; an action that declares none caches nothing. The old hook names are refused at class creation.
    ACCESS: Optional object check, declared with ``@access_decide`` on a method whose name carries the ``_access_decide`` suffix — run after ``@check_roles`` passes, at most one per operation and never inherited. An operation that declares none has no object check.
    AI-CORE-END
    """

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Enforce the ``"Action"`` name suffix, and the rules of the cache declarations, for every subclass."""
        super().__init_subclass__(**kwargs)

        if not cls.__name__.endswith(_REQUIRED_SUFFIX):
            raise NamingSuffixError(
                f"Class '{cls.__name__}' inherits BaseAction but lacks the "
                f"'{_REQUIRED_SUFFIX}' suffix. "
                f"Rename to '{cls.__name__}{_REQUIRED_SUFFIX}'.",
            )
        validate_cache_declarations(cls)

    def get_full_class_name(self) -> str:
        """``module.qualname`` via :meth:`TypeIntrospection.full_qualname` (plugins, logging)."""
        return TypeIntrospection.full_qualname(self.__class__)
