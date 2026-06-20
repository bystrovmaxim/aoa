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
(``cache_coordinator=...``). When it is ``None`` (default), the engine does **not**
call ``cache_key``, ``read_cache``, or ``on_cache_write`` on actions.

The coordinator lives on the **machine instance**, not on ``BaseAction``. Do **not**
use a ``ClassVar`` (or similar) on the action class to hold a cache or coordinator;
that pattern is out of scope for v1.

**v1 does not implement single-flight (de-duplication of in-flight runs).** Parallel
callers with the same key may each run the pipeline until entries exist.

Subclasses may override:

- ``cache_key(params) -> str | None`` — return ``None`` to skip the cache for this
  call. For data scoped to a **subject** (for example a signed-in user), the key
  segment **must** include that scope (for example ``user_id``), so tenants do not
  share entries by accident.
- ``read_cache(params, entry) -> R | None`` — interpret ``entry``; return ``None``
  to treat the row as stale or unusable (the machine invalidates that key and runs
  the pipeline).
- ``on_cache_write(result, params, duration_ms) -> bool`` — return whether the
  machine should **persist** ``result`` after a successful pipeline. The action does
  **not** write to the coordinator itself.

Results produced only via a matching ``@on_error`` handler (**handled error path**)
are **not** written to the cache, even when ``on_cache_write`` would return ``True``.

If a cache hook, validation of its return value, or a coordinator method raises,
the exception propagates to the caller. In v1 the machine does **not** emit
``GlobalFinishEvent`` when that happens after ``GlobalStartEvent`` (same class of
lifecycle gap as an unhandled pipeline error). :exc:`CacheContractError` is raised
when a hook return value violates the typed contract (for example wrong type or
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
from typing import Any, cast

from aoa.action_machine.intents.aspects.aspect_intent import AspectIntent
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
from aoa.action_machine.system_core.type_introspection import TypeIntrospection
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.model.base_result import BaseResult
from aoa.action_machine.exceptions.naming_suffix_error import NamingSuffixError
from aoa.action_machine.runtime.cache_entry import CacheEntry
from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model

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
    CompensateIntent,
    ConnectionIntent,
    OnErrorIntent,
    ContextRequiresIntent,
    SensitiveIntent,
):
    """
    AI-CORE-BEGIN
    ROLE: Public base type for all async/sync actions.
    CONTRACT: Subclasses end with ``Action``; carry marker mixins; use required decorators.
    INVARIANTS: Stateless at instance level regarding metadata.
    CACHE: Optional ``cache_key`` / ``read_cache`` / ``on_cache_write``; defaults disable caching writes and leave keying to ``None``.
    AI-CORE-END
"""

    def cache_key(self, params: P) -> str | None:
        """User key segment for this run; ``None`` skips cache read/write for the call."""
        return None

    async def read_cache(self, params: P, entry: CacheEntry) -> R | None:
        """Return a typed hit from ``entry``, or ``None`` so the machine invalidates and re-runs."""
        return cast("R", entry.result)

    async def on_cache_write(self, result: R, params: P, duration_ms: float) -> bool:
        """Whether the machine should ``put`` ``result`` after a clean summary (not ``@on_error``-only)."""
        return False

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Enforce the ``"Action"`` name suffix for every concrete subclass."""
        super().__init_subclass__(**kwargs)

        if not cls.__name__.endswith(_REQUIRED_SUFFIX):
            raise NamingSuffixError(
                f"Class '{cls.__name__}' inherits BaseAction but lacks the "
                f"'{_REQUIRED_SUFFIX}' suffix. "
                f"Rename to '{cls.__name__}{_REQUIRED_SUFFIX}'.",
            )

    def get_full_class_name(self) -> str:
        """``module.qualname`` via :meth:`TypeIntrospection.full_qualname` (plugins, logging)."""
        return TypeIntrospection.full_qualname(self.__class__)
