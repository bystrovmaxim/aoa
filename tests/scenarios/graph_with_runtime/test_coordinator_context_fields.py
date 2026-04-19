# tests/scenarios/graph_with_runtime/test_coordinator_context_fields.py
"""
@context_requires metadata: runtime metadata cache and facet graph.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Ensures context keys declared via ``@context_requires`` land in facet snapshots
the way the runtime sees them: on regular aspects and on ``@on_error`` handlers.
After ``build()``, the coordinator exposes them through
``get_snapshot(cls, "aspect")`` / ``get_snapshot(cls, "error_handler")``, etc.

═══════════════════════════════════════════════════════════════════════════════
MODEL EVOLUTION (why tests are no longer about “context_field nodes”)
═══════════════════════════════════════════════════════════════════════════════

In an early coordinator model, **separate** ``context_field`` **nodes** and
``requires_context`` **edges** visualized context needs on the graph: two aspects
with the same key pointed at one field node, and reuse was obvious on the diagram.

After moving to **transactional graph build from FacetVertex**, the visual
“each context field = node” detail **is not duplicated** the same way: context
remains **step semantics** — a tuple of string keys on ``AspectMeta``,
``OnErrorMeta``, etc. — while the graph describes facets (role, meta, aspect, …)
and structural edges (depends, connection, belongs_to, …). That is a deliberate
trade-off: less noise in PyDiGraph, richer executable snapshot model.

This file **does not** drop the reuse invariant: two aspects with ``user.user_id``
must still expose the same key in their ``context_keys``; we assert consistency
at the **metadata** level, not by counting graph nodes.

═══════════════════════════════════════════════════════════════════════════════
DEPENDENCY FACTORY CACHE CLEAR
═══════════════════════════════════════════════════════════════════════════════

``clear_dependency_factory_cache(coordinator)`` clears only the dependency-factory
cache on the coordinator; the built facet graph and facet snapshots are not
rebuilt — context keys on aspects remain readable.

═══════════════════════════════════════════════════════════════════════════════
TEST ACTIONS
═══════════════════════════════════════════════════════════════════════════════

Classes are declared **inside this test module** (not under scenarios/domain_model/)
to avoid polluting domain fixtures and keep scenarios narrow:

- one aspect with two context keys;
- two aspects sharing ``user.user_id``;
- ``@on_error`` with its own key set;
- aspects without ``@context_requires`` (empty ``context_keys``).
"""

from pydantic import Field

from action_machine.context.ctx_constants import Ctx
from action_machine.intents.aspects.regular_aspect_decorator import regular_aspect
from action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from action_machine.intents.check_roles import NoneRole, check_roles
from action_machine.intents.context.context_requires_decorator import context_requires
from action_machine.intents.meta.meta_decorator import meta
from action_machine.intents.on_error.on_error_decorator import on_error
from action_machine.legacy.core import Core
from action_machine.model.base_action import BaseAction
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from action_machine.model.base_state import BaseState
from action_machine.resources.base_resource_manager import BaseResourceManager
from action_machine.runtime.dependency_factory import clear_dependency_factory_cache
from action_machine.runtime.tools_box import ToolsBox
from graph.graph_coordinator import GraphCoordinator
from tests.scenarios.domain_model.domains import SystemDomain


def _regular_aspects(coordinator: GraphCoordinator, cls: type):
    snap = coordinator.get_snapshot(cls, "aspect")
    if snap is None or not hasattr(snap, "aspects"):
        return ()
    return tuple(a for a in snap.aspects if a.aspect_type == "regular")


def _error_handlers(coordinator: GraphCoordinator, cls: type):
    snap = coordinator.get_snapshot(cls, "error_handler")
    if snap is None or not hasattr(snap, "error_handlers"):
        return ()
    return tuple(snap.error_handlers)


# ═════════════════════════════════════════════════════════════════════════════
# Test helpers
# ═════════════════════════════════════════════════════════════════════════════


class _CtxTestParams(BaseParams):
    """Params for minimal actions in context_requires scenarios."""

    value: str = Field(description="Test value")


class _CtxTestResult(BaseResult):
    """Result for minimal actions in context_requires scenarios."""

    status: str = Field(description="Status")


# ═════════════════════════════════════════════════════════════════════════════
# Test actions (narrow edge cases, not exported to scenarios.domain_model)
# ═════════════════════════════════════════════════════════════════════════════


@meta(description="Action with one aspect and context_requires", domain=SystemDomain)
@check_roles(NoneRole)
class _SingleContextAction(BaseAction[_CtxTestParams, _CtxTestResult]):
    """One regular aspect requests ``user.user_id`` and ``request.trace_id``."""

    @regular_aspect("Audit")
    @context_requires(Ctx.User.user_id, Ctx.Request.trace_id)
    async def audit_aspect(
        self, params: _CtxTestParams, state: BaseState,
        box: ToolsBox, connections: dict[str, BaseResourceManager],
        ctx: object,
    ) -> dict:
        return {}

    @summary_aspect("Result")
    async def result_summary(
        self, params: _CtxTestParams, state: BaseState,
        box: ToolsBox, connections: dict[str, BaseResourceManager],
    ) -> _CtxTestResult:
        return _CtxTestResult(status="ok")


@meta(description="Action with two aspects requesting the same field", domain=SystemDomain)
@check_roles(NoneRole)
class _SharedContextFieldAction(BaseAction[_CtxTestParams, _CtxTestResult]):
    """Two aspects share ``user.user_id``; the second adds ``user.roles``."""

    @regular_aspect("First aspect")
    @context_requires(Ctx.User.user_id)
    async def first_aspect(
        self, params: _CtxTestParams, state: BaseState,
        box: ToolsBox, connections: dict[str, BaseResourceManager],
        ctx: object,
    ) -> dict:
        return {}

    @regular_aspect("Second aspect")
    @context_requires(Ctx.User.user_id, Ctx.User.roles)
    async def second_aspect(
        self, params: _CtxTestParams, state: BaseState,
        box: ToolsBox, connections: dict[str, BaseResourceManager],
        ctx: object,
    ) -> dict:
        return {}

    @summary_aspect("Result")
    async def result_summary(
        self, params: _CtxTestParams, state: BaseState,
        box: ToolsBox, connections: dict[str, BaseResourceManager],
    ) -> _CtxTestResult:
        return _CtxTestResult(status="ok")


@meta(description="Action with on_error and context_requires", domain=SystemDomain)
@check_roles(NoneRole)
class _ErrorHandlerContextAction(BaseAction[_CtxTestParams, _CtxTestResult]):
    """``ValueError`` handler requires ``user.user_id`` and ``request.client_ip``."""

    @regular_aspect("Operation")
    async def operation_aspect(
        self, params: _CtxTestParams, state: BaseState,
        box: ToolsBox, connections: dict[str, BaseResourceManager],
    ) -> dict:
        return {}

    @summary_aspect("Result")
    async def result_summary(
        self, params: _CtxTestParams, state: BaseState,
        box: ToolsBox, connections: dict[str, BaseResourceManager],
    ) -> _CtxTestResult:
        return _CtxTestResult(status="ok")

    @on_error(ValueError, description="Handling with context")
    @context_requires(Ctx.User.user_id, Ctx.Request.client_ip)
    async def handle_value_on_error(
        self, params: _CtxTestParams, state: BaseState,
        box: ToolsBox, connections: dict[str, BaseResourceManager],
        error: Exception, ctx: object,
    ) -> _CtxTestResult:
        return _CtxTestResult(status="error_handled")


@meta(description="Action without context_requires", domain=SystemDomain)
@check_roles(NoneRole)
class _NoContextAction(BaseAction[_CtxTestParams, _CtxTestResult]):
    """No method uses ``@context_requires`` — expect empty ``context_keys``."""

    @regular_aspect("Simple aspect")
    async def simple_aspect(
        self, params: _CtxTestParams, state: BaseState,
        box: ToolsBox, connections: dict[str, BaseResourceManager],
    ) -> dict:
        return {}

    @summary_aspect("Result")
    async def result_summary(
        self, params: _CtxTestParams, state: BaseState,
        box: ToolsBox, connections: dict[str, BaseResourceManager],
    ) -> _CtxTestResult:
        return _CtxTestResult(status="ok")


# ═════════════════════════════════════════════════════════════════════════════
# Runtime metadata and context keys
# ═════════════════════════════════════════════════════════════════════════════


class TestContextKeysViaMetadata:
    """``context_keys`` on aspects and handlers via facet snapshots."""

    def test_aspect_context_keys(self) -> None:
        coordinator = Core.create_coordinator()
        audit = next(
            a for a in _regular_aspects(coordinator,_SingleContextAction)
            if a.method_name == "audit_aspect"
        )
        assert "user.user_id" in audit.context_keys
        assert "request.trace_id" in audit.context_keys

    def test_shared_user_id_across_aspects(self) -> None:
        """Both aspects see ``user.user_id``; only the second adds ``user.roles``."""

        coordinator = Core.create_coordinator()
        first = next(
            a for a in _regular_aspects(coordinator,_SharedContextFieldAction)
            if a.method_name == "first_aspect"
        )
        second = next(
            a for a in _regular_aspects(coordinator,_SharedContextFieldAction)
            if a.method_name == "second_aspect"
        )
        assert "user.user_id" in first.context_keys
        assert "user.user_id" in second.context_keys
        assert "user.roles" in second.context_keys
        assert "user.roles" not in first.context_keys

    def test_no_context_keys_when_undeclrared(self) -> None:
        """Without the decorator — empty key set on the regular aspect."""

        coordinator = Core.create_coordinator()
        simple = next(
            a for a in _regular_aspects(coordinator,_NoContextAction)
            if a.method_name == "simple_aspect"
        )
        assert len(simple.context_keys) == 0

    def test_error_handler_context_keys(self) -> None:
        """``OnErrorMeta`` gets the same string paths the handler declared."""

        coordinator = Core.create_coordinator()
        handler = next(
            h for h in _error_handlers(coordinator,_ErrorHandlerContextAction)
            if h.method_name == "handle_value_on_error"
        )
        assert "user.user_id" in handler.context_keys
        assert "request.client_ip" in handler.context_keys


class TestContextMetadataAfterFactoryCacheClear:
    """``context_keys`` stability after dependency-factory cache clear."""

    def test_reread_context_keys_stable(self) -> None:
        """Re-reading from a built coordinator returns the same ``context_keys``."""
        coordinator = Core.create_coordinator()
        audit = next(
            a for a in _regular_aspects(coordinator,_SingleContextAction)
            if a.method_name == "audit_aspect"
        )
        assert "user.user_id" in audit.context_keys

    def test_factory_cache_clear_preserves_context_keys(self) -> None:
        """
        Clearing factory cache does not break reading context keys from facet snapshots.
        """
        coordinator = Core.create_coordinator()
        clear_dependency_factory_cache(coordinator)
        audit = next(
            a for a in _regular_aspects(coordinator,_SingleContextAction)
            if a.method_name == "audit_aspect"
        )
        assert "user.user_id" in audit.context_keys
