# src/action_machine/runtime/aspect_executor.py
"""
Aspect executor component wrapper.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provide a dedicated component for aspect execution in machine orchestration.
This component owns regular/summary execution paths, including
``context_requires`` handling, checker validation, and immutable state merge.
``execute_regular`` and ``execute_summary`` share ``call_aspect`` as the sole
aspect-method dispatcher (facet ``AspectIntentInspector`` only; not compensators
or saga rollback).

Logging metadata (``LogCoordinator``, ``mode``, ``machine_class_name``) is
injected at construction so aspect calls stay decoupled from machine internals.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    ActionProductMachine
        │
        ├── AspectExecutor(log_coordinator, machine_class_name, mode)
        │
        ├── execute_regular(...)
        │       ├── call_aspect(...)
        │       ├── checker application (on failure: saga frame with
        │       │       state_after=None, then raise)
        │       ├── state merge
        │       └── optional saga frame append (state_after=merged)
        │
        └── execute_summary(...)
                └── call_aspect(...)

"""

from __future__ import annotations

import time
from typing import Any, Protocol

from action_machine.context.context_view import ContextView
from action_machine.exceptions import ValidationFieldError
from action_machine.legacy.binding.action_result_binding import (
    bind_pipeline_result_to_action,
    synthetic_summary_result_when_missing_aspect,
)
from action_machine.logging.domain_resolver import resolve_domain
from action_machine.logging.log_coordinator import LogCoordinator
from action_machine.logging.scoped_logger import ScopedLogger
from action_machine.model.base_action import BaseAction
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from action_machine.model.base_state import BaseState
from action_machine.model.graph_model.checker_graph_node import CheckerGraphNode
from action_machine.model.graph_model.regular_aspect_graph_node import RegularAspectGraphNode
from action_machine.model.graph_model.summary_aspect_graph_node import SummaryAspectGraphNode
from action_machine.resources.base_resource import BaseResource
from action_machine.runtime.saga_frame import SagaFrame
from action_machine.runtime.tools_box import ToolsBox


class AspectExecutor:
    """Regular and summary pipelines; shared primitive ``call_aspect`` invokes only facet aspect methods."""

    def __init__(
        self,
        log_coordinator: LogCoordinator,
        *,
        machine_class_name: str,
        mode: str,
    ) -> None:
        self._log_coordinator = log_coordinator
        self._machine_class_name = machine_class_name
        self._mode = mode

    @staticmethod
    def _apply_checker_graph_nodes(
        checker_nodes: list[CheckerGraphNode],
        result: dict[str, Any],
    ) -> None:
        """Run checker instances from interchange vertices against a regular-aspect state patch."""
        for cn in checker_nodes:
            payload = cn.node_obj
            extras = {
                k: v
                for k, v in payload.properties.items()
                if k not in ("TypeChecker", "required")
            }
            checker_instance = payload.checker_class(
                payload.field_name,
                required=payload.required,
                **extras,
            )
            checker_instance.check(result)

    async def call_aspect(
        self,
        *,
        aspect_node: RegularAspectGraphNode | SummaryAspectGraphNode,
        action: BaseAction[Any, Any],
        params: BaseParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
        context: Any,
    ) -> Any:
        """
        Shared primitive: invoke one regular or summary aspect callable only.

        Not for compensators, saga rollback, ``@on_error``, or non-aspect hooks.
        ``aspect_node`` is a regular or summary interchange vertex; wraps ``node_obj`` with scoped log / ``ContextView``.
        """
        aspect_log = ScopedLogger(
            coordinator=self._log_coordinator,
            nest_level=box.nested_level,
            machine_name=self._machine_class_name,
            mode=self._mode,
            action_name=action.get_full_class_name(),
            aspect_name=aspect_node.label,
            context=context,
            state=state,
            params=params,
            domain=resolve_domain(type(action)),
        )
        aspect_box = ToolsBox(
            run_child=box.run_child,
            factory=box.factory,
            resources=box.resources,
            log=aspect_log,
            nested_level=box.nested_level,
            rollup=box.rollup,
        )
        context_keys = aspect_node.get_required_context_keys()
        if context_keys:
            ctx_view = ContextView(context, context_keys)
            return await aspect_node.node_obj(
                action, params, state, aspect_box, connections, ctx_view,
            )
        return await aspect_node.node_obj(
            action, params, state, aspect_box, connections,
        )

    async def execute_regular(
        self,
        *,
        aspect_node: RegularAspectGraphNode,
        action: BaseAction[Any, Any],
        params: BaseParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
        context: Any,
        runtime: _RuntimeLike,
        saga_stack: list[SagaFrame],
    ) -> tuple[BaseState, dict[str, Any], float]:
        """Execute one regular aspect with checker validation and state merge."""
        state_before = state
        aspect_start = time.time()
        new_state_dict = await self.call_aspect(
            aspect_node=aspect_node,
            action=action,
            params=params,
            state=state,
            box=box,
            connections=connections,
            context=context,
        )
        if not isinstance(new_state_dict, dict):
            raise TypeError(
                f"Aspect {aspect_node.label} must return a dict, "
                f"got {type(new_state_dict).__name__}"
            )

        checker_nodes = aspect_node.get_checker_graph_nodes()

        def _append_checker_rejected_frame() -> None:
            if not runtime.has_compensators:
                return
            saga_stack.append(
                SagaFrame(
                    compensator=runtime.compensators_by_aspect.get(
                        aspect_node.label,
                    ),
                    aspect_name=aspect_node.label,
                    state_before=state_before,
                    state_after=None,
                )
            )

        try:
            if not checker_nodes and new_state_dict:
                raise ValidationFieldError(
                    f"Aspect {aspect_node.label} has no checkers, "
                    f"but returned non-empty state: {new_state_dict}. "
                    f"Either add checkers for all fields, or return an empty dict."
                )
            if checker_nodes:
                allowed_fields = {cn.label for cn in checker_nodes}
                extra_fields = set(new_state_dict.keys()) - allowed_fields
                if extra_fields:
                    raise ValidationFieldError(
                        f"Aspect {aspect_node.label} returned extra fields: "
                        f"{extra_fields}. Allowed only: {allowed_fields}"
                    )
                self._apply_checker_graph_nodes(checker_nodes, new_state_dict)
        except ValidationFieldError:
            _append_checker_rejected_frame()
            raise

        merged_state = BaseState(**{**state.to_dict(), **new_state_dict})
        if runtime.has_compensators:
            compensator = runtime.compensators_by_aspect.get(aspect_node.label)
            saga_stack.append(
                SagaFrame(
                    compensator=compensator,
                    aspect_name=aspect_node.label,
                    state_before=state_before,
                    state_after=merged_state,
                )
            )

        duration_s = time.time() - aspect_start
        return merged_state, new_state_dict, duration_s

    async def execute_summary(
        self,
        *,
        summary_node: SummaryAspectGraphNode | None,
        action: BaseAction[Any, Any],
        params: BaseParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
        context: Any,
    ) -> tuple[BaseResult, float]:
        """Execute summary aspect and return result with duration."""
        action_cls = type(action)
        if summary_node is None:
            return synthetic_summary_result_when_missing_aspect(action_cls), 0.0
        summary_start = time.time()
        raw = await self.call_aspect(
            aspect_node=summary_node,
            action=action,
            params=params,
            state=state,
            box=box,
            connections=connections,
            context=context,
        )
        result = bind_pipeline_result_to_action(
            action_cls,
            raw,
            source=f"summary aspect `{summary_node.label}`",
        )
        return result, (time.time() - summary_start)


class _RuntimeLike(Protocol):
    @property
    def has_compensators(self) -> bool: ...

    @property
    def compensators_by_aspect(self) -> dict[str, Any]: ...
