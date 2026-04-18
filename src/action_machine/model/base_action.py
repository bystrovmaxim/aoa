# src/action_machine/model/base_action.py
"""
Abstract base class for every ActionMachine action (user-defined command).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``BaseAction`` is parameterized by frozen Pydantic types ``P`` (params) and ``R``
(result). Subclasses declare behavior with class- and method-level decorators;
markers in the MRO enable those decorators. Runtime execution and metadata reads
go through ``GraphCoordinator`` facet snapshots (built by intent inspectors),
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
  ``GraphCoordinator.build()``.
- This class does **not** hold a coordinator reference or expose ``get_metadata``.

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

    ActionMetaIntent       → ``@meta`` (required)
    RoleIntent             → ``@check_roles``
    DependencyIntent       → ``@depends``
    CheckerIntent          → result / field checkers on aspect methods
    AspectIntent           → ``@regular_aspect`` / ``@summary_aspect``
    CompensateIntent       → ``@compensate``
    ConnectionIntent       → ``@connection``
    OnErrorIntent          → ``@on_error``
    ContextRequiresIntent  → ``@context_requires``

Class-level decorators validate the marker immediately; method-level decorators
are validated when the coordinator runs inspectors on the class.

The graph inspector for ``BaseAction[P, R]`` schema bindings is
:class:`ActionTypedSchemasInspector` at the end of this module (imports deferred
until after ``BaseAction`` is defined to avoid cycles with
:mod:`action_machine.runtime.binding.extract_action_params_result_types`).

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

from action_machine.dependencies.dependency_intent import DependencyIntent
from action_machine.intents.aspects.aspect_intent import AspectIntent
from action_machine.intents.auth.role_intent import RoleIntent
from action_machine.intents.checkers.checker_intent import CheckerIntent
from action_machine.intents.compensate.compensate_intent import CompensateIntent
from action_machine.intents.context.context_requires_intent import ContextRequiresIntent
from action_machine.intents.meta.meta_intents import ActionMetaIntent
from action_machine.intents.on_error.on_error_intent import OnErrorIntent
from action_machine.model.base_schema import BaseSchema
from action_machine.model.exceptions import NamingSuffixError
from action_machine.resources.connection_intent import ConnectionIntent

_REQUIRED_SUFFIX = "Action"


class BaseAction[P: BaseSchema, R: BaseSchema](
    ABC,
    ActionMetaIntent,
    RoleIntent,
    DependencyIntent[object],
    CheckerIntent,
    AspectIntent,
    CompensateIntent,
    ConnectionIntent,
    OnErrorIntent,
    ContextRequiresIntent,
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


# ---------------------------------------------------------------------------
# Graph facet: ``BaseAction[P, R]`` → ``described_fields`` (registered by runtime)
# Imports live here so :mod:`action_machine.runtime.binding.extract_action_params_result_types`
# can import ``BaseAction`` above without a partially-initialized cycle.
# ---------------------------------------------------------------------------

# pylint: disable=wrong-import-order,wrong-import-position
from dataclasses import dataclass  # noqa: E402

from action_machine.graph.base_facet_snapshot import BaseFacetSnapshot  # noqa: E402
from action_machine.graph.base_intent_inspector import BaseIntentInspector  # noqa: E402
from action_machine.graph.payload import EdgeInfo, FacetPayload  # noqa: E402
from action_machine.intents.described_fields.described_fields_intent_inspector import (  # noqa: E402
    DescribedFieldsIntentInspector,
)
from action_machine.interchange_vertex_labels import ACTION_VERTEX_TYPE  # noqa: E402
from action_machine.runtime.binding.extract_action_params_result_types import (  # noqa: E402
    extract_action_params_result_types,
)
# pylint: enable=wrong-import-order,wrong-import-position


class ActionTypedSchemasInspector(BaseIntentInspector):
    """
    Graph: link each ``BaseAction`` subclass to resolved ``P`` / ``R`` schema types.

    Emits a merged ``action`` facet row with ``uses_params`` / ``uses_result`` edges
    to canonical ``params_schema`` / ``result_schema`` (or ``entity`` / ``described_fields``)
    hosts; snapshot key ``action_schemas``.
    See module docstring at top of this file for the full contract.

    AI-CORE-BEGIN
    ROLE: Concrete inspector for action-to-schema graph mapping.
    CONTRACT: Merged ``action`` payloads; snapshot storage key ``action_schemas``.
    AI-CORE-END
    """

    _target_intent: type = BaseAction

    @dataclass(frozen=True)
    class Snapshot(BaseFacetSnapshot):
        """Typed view: which schema classes an action uses."""

        class_ref: type
        params_type: type | None
        result_type: type | None

        def to_facet_payload(self) -> FacetPayload:
            edges: list[EdgeInfo] = []
            if self.params_type is not None:
                p_nt, p_name = DescribedFieldsIntentInspector.facet_host_for_schema_type(
                    self.params_type,
                )
                edges.append(
                    EdgeInfo(
                        target_node_type=p_nt,
                        target_name=p_name,
                        edge_type="uses_params",
                        is_structural=False,
                        target_class_ref=self.params_type,
                    ),
                )
            if self.result_type is not None:
                r_nt, r_name = DescribedFieldsIntentInspector.facet_host_for_schema_type(
                    self.result_type,
                )
                edges.append(
                    EdgeInfo(
                        target_node_type=r_nt,
                        target_name=r_name,
                        edge_type="uses_result",
                        is_structural=False,
                        target_class_ref=self.result_type,
                    ),
                )
            return FacetPayload(
                node_type=ACTION_VERTEX_TYPE,
                node_name=ActionTypedSchemasInspector._make_node_name(self.class_ref),
                node_class=self.class_ref,
                node_meta=ActionTypedSchemasInspector._make_meta(
                    params_type=self.params_type,
                    result_type=self.result_type,
                ),
                edges=tuple(edges),
            )

    @classmethod
    def _subclasses_recursive(cls) -> list[type]:
        return cls._collect_subclasses(cls._target_intent)

    @classmethod
    def inspect(cls, target_cls: type) -> FacetPayload | None:
        p_type, r_type = extract_action_params_result_types(target_cls)
        if p_type is None and r_type is None:
            return None
        return cls._build_payload(target_cls)

    @classmethod
    def facet_snapshot_for_class(cls, target_cls: type) -> Snapshot | None:
        p_type, r_type = extract_action_params_result_types(target_cls)
        if p_type is None and r_type is None:
            return None
        return cls.Snapshot(
            class_ref=target_cls,
            params_type=p_type,
            result_type=r_type,
        )

    @classmethod
    def facet_snapshot_storage_key(
        cls, _target_cls: type, _payload: FacetPayload,
    ) -> str:
        return "action_schemas"

    @classmethod
    def _build_payload(cls, target_cls: type) -> FacetPayload:
        snap = cls.facet_snapshot_for_class(target_cls)
        assert snap is not None
        return snap.to_facet_payload()
