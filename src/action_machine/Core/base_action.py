# src/action_machine/core/base_action.py
"""
Abstract base class for every ActionMachine action (user-defined command).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``BaseAction`` is parameterized by frozen Pydantic types ``P`` (params) and ``R``
(result). Subclasses declare behavior with class- and method-level decorators;
markers in the MRO enable those decorators. Runtime execution and metadata reads
go through ``GateCoordinator`` facet snapshots (built by gate-host inspectors),
not through helper APIs on this class.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Every concrete subclass name must end with ``"Action"`` (enforced in
  ``__init_subclass__`` via ``NamingSuffixError``).
- Every action class must use ``@meta(...)`` and ``@check_roles(...)``.
- Declaration scratch (``_role_info``, ``_connection_info``, method-level
  ``_new_aspect_meta``, ``_checker_meta``, etc.) is written by decorators;
  **inspection** for the graph belongs to **inspectors** during
  ``GateCoordinator.build()``.
- This class does **not** hold a coordinator reference or expose ``get_metadata``.

═══════════════════════════════════════════════════════════════════════════════
DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    Decorators (import time)
         │
         ▼
    Class-level / method-level scratch attrs on the action class
         │
         ▼
    GateCoordinator.build()  →  inspectors  →  facet snapshots + graph
         │
         ▼
    ActionProductMachine.run()  →  get_snapshot(action_cls, facet_key)

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE — MARKER MIXINS
═══════════════════════════════════════════════════════════════════════════════

``BaseAction`` inherits marker mixins only (no inspector logic):

    ActionMetaGateHost       → ``@meta`` (required)
    RoleGateHost             → ``@check_roles``
    DependencyGateHost       → ``@depends``
    CheckerGateHost          → result / field checkers on aspect methods
    AspectGateHost           → ``@regular_aspect`` / ``@summary_aspect``
    CompensateGateHost       → ``@compensate``
    ConnectionGateHost       → ``@connection``
    OnErrorGateHost          → ``@on_error``
    ContextRequiresGateHost  → ``@context_requires``

Class-level decorators validate the marker immediately; method-level decorators
are validated when the coordinator runs inspectors on the class.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path::

    @meta(description="Ping", domain=SystemDomain)
    @check_roles(ROLE_NONE)
    class PingAction(BaseAction[BaseParams, BaseResult]):
        @summary_aspect("Pong")
        async def pong_summary(self, params, state, box, connections):
            return BaseResult()

Edge case: ``class Bad(BaseAction[BaseParams, BaseResult]):`` (name not ending in
``"Action"``) raises ``NamingSuffixError`` in ``__init_subclass__``.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Aspects receive immutable ``BaseState``; they return dict merges, not in-place
  mutation.
- ``ToolsBox`` does not expose raw ``Context``; use ``@context_requires`` and
  ``ContextView``.
- ``@on_error`` handlers are not inherited from base action classes; each action
  declares its own.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Core action base type; decorator surface for the action pipeline.
CONTRACT: Generic ``BaseAction[P,R]``; naming suffix; required ``@meta``/``@check_roles``.
INVARIANTS: Markers only; no coordinator; no scratch introspection API on class.
FLOW: decorators → class attrs → coordinator build → machine reads snapshots.
FAILURES: ``NamingSuffixError`` on bad class name; decorator-time errors on bad use.
EXTENSION POINTS: plugins match on ``get_full_class_name()``; facets extend via inspectors.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from abc import ABC
from typing import Any

from action_machine.aspects.aspect_gate_host import AspectGateHost
from action_machine.auth.role_gate_host import RoleGateHost
from action_machine.checkers.checker_gate_host import CheckerGateHost
from action_machine.compensate.compensate_gate_host import CompensateGateHost
from action_machine.context.context_requires_gate_host import ContextRequiresGateHost
from action_machine.core.base_schema import BaseSchema
from action_machine.core.exceptions import NamingSuffixError
from action_machine.core.meta_gate_hosts import ActionMetaGateHost
from action_machine.dependencies.dependency_gate_host import DependencyGateHost
from action_machine.on_error.on_error_gate_host import OnErrorGateHost
from action_machine.resource_managers.connection_gate_host import ConnectionGateHost

_REQUIRED_SUFFIX = "Action"


class BaseAction[P: BaseSchema, R: BaseSchema](
    ABC,
    ActionMetaGateHost,
    RoleGateHost,
    DependencyGateHost[object],
    CheckerGateHost,
    AspectGateHost,
    CompensateGateHost,
    ConnectionGateHost,
    OnErrorGateHost,
    ContextRequiresGateHost,
):
    """
    Abstract action: decorators declare pipeline behavior; runtime uses coordinator snapshots.

    AI-CORE-BEGIN
    ROLE: Public base type for all async/sync actions.
    CONTRACT: Subclasses end with ``Action``; carry marker mixins; use required decorators.
    INVARIANTS: Stateless at instance level regarding metadata; ``_full_class_name`` cache on class.
    AI-CORE-END
    """

    _full_class_name: str | None = None

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
        """
        Return ``module.qualname`` for this action class, cached on the class.

        Used by plugins (e.g. regex filters) to decide which hooks apply.
        """
        if self.__class__._full_class_name is None:
            module: str = self.__class__.__module__ or ""
            self.__class__._full_class_name = f"{module}.{self.__class__.__qualname__}"
        return self.__class__._full_class_name
