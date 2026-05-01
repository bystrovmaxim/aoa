# src/action_machine/model/base_action.py
"""
Abstract base class for every ActionMachine action (user-defined command).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``BaseAction`` is parameterized by ``P`` (a ``BaseParams`` subclass) and ``R``
(a ``BaseResult`` subclass). Subclasses declare behavior with class- and method-level decorators;
markers in the MRO enable those decorators. Runtime execution and metadata reads
go through ``GraphCoordinator`` facet snapshots (built by intent inspectors),
not through helper APIs on this class.

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
    GraphCoordinator.build()  →  inspectors  →  facet snapshots + graph
         │
         ▼
    ActionProductMachine.run()  →  get_snapshot(action_cls, facet_key)

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

Class-level decorators validate the marker immediately; method-level decorators
are validated when the coordinator runs inspectors on the class.

The legacy graph inspector for ``BaseAction[P, R]`` schema bindings is
:class:`~action_machine.legacy.action_typed_schemas_inspector.ActionTypedSchemasInspector`
(so :mod:`action_machine.model.base_action` avoids extractor imports at module tail).

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path::

    @meta(description="Ping", domain=SystemDomain)
    @check_roles(NoneRole)
    class PingAction(BaseAction[BaseParams, BaseResult]):
        @summary_aspect("Pong")
        async def pong_summary(self, params, state, box, connections):
            return BaseResult()

Edge case: ``class Bad(BaseAction[BaseParams, BaseResult]):`` (name not ending in
``"Action"``) raises ``NamingSuffixError`` in ``__init_subclass__``.
"""

from __future__ import annotations

from abc import ABC
from typing import Any

from action_machine.intents.aspects.aspect_intent import AspectIntent
from action_machine.intents.check_roles.check_roles_intent import CheckRolesIntent
from action_machine.intents.checkers.checker_intent import CheckerIntent
from action_machine.intents.compensate.compensate_intent import CompensateIntent
from action_machine.intents.connection.connection_intent import ConnectionIntent
from action_machine.intents.context_requires.context_requires_intent import ContextRequiresIntent
from action_machine.intents.depends.depends_eligible import DependsEligible
from action_machine.intents.depends.depends_intent import DependsIntent
from action_machine.intents.meta.meta_intent import MetaIntent
from action_machine.intents.on_error.on_error_intent import OnErrorIntent
from action_machine.system_core.type_introspection import TypeIntrospection
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from action_machine.exceptions import NamingSuffixError
from graph.exclude_graph_model import exclude_graph_model

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
):
    """
AI-CORE-BEGIN
    ROLE: Public base type for all async/sync actions.
    CONTRACT: Subclasses end with ``Action``; carry marker mixins; use required decorators.
    INVARIANTS: Stateless at instance level regarding metadata.
    AI-CORE-END
"""

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
