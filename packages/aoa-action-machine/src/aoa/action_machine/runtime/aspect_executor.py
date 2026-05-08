# packages/aoa-action-machine/src/aoa/action_machine/runtime/aspect_executor.py
"""
Aspect executor component wrapper.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provide a dedicated component for aspect execution in machine orchestration.
This component owns regular/summary execution paths, including
``context_requires`` handling, checker validation, and immutable state merge.
``execute_regular`` and ``execute_summary`` share ``call_aspect`` as the sole
aspect-method dispatcher for regular pipeline aspects (not compensators or saga rollback).

``LogCoordinator`` is injected at construction so aspect calls stay decoupled
from machine internals.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    ActionProductMachine
        │
        ├── AspectExecutor(log_coordinator)
        │
        ├── execute_regular(...)
        │       ├── call_aspect(...)
        │       ├── state merge
        │       └── checker application
        │
        └── execute_summary(...)
                └── call_aspect(...)

"""

from __future__ import annotations

import time
from typing import Any, cast

from aoa.action_machine.context.context_view import ContextView
from aoa.action_machine.exceptions.missing_summary_aspect_error import MissingSummaryAspectError
from aoa.action_machine.exceptions.validation_field_error import ValidationFieldError
from aoa.action_machine.graph_model.nodes.checker_graph_node import CheckerGraphNode
from aoa.action_machine.graph_model.nodes.regular_aspect_graph_node import RegularAspectGraphNode
from aoa.action_machine.graph_model.nodes.summary_aspect_graph_node import SummaryAspectGraphNode
from aoa.action_machine.intents.action_schema.action_schema_intent_resolver import (
    ActionSchemaIntentResolver,
)
from aoa.action_machine.logging.domain_resolver import resolve_domain
from aoa.action_machine.logging.log_coordinator import LogCoordinator
from aoa.action_machine.logging.scoped_logger import ScopedLogger
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.model.base_result import BaseResult
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.runtime.tools_box import ToolsBox


class AspectExecutor:
    """Regular and summary pipelines; shared primitive ``call_aspect`` invokes only interchange aspect methods."""

    def __init__(
        self,
        log_coordinator: LogCoordinator,
    ) -> None:
        self._log_coordinator = log_coordinator

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
        action: BaseAction[Any, Any],
        aspect_node: RegularAspectGraphNode | SummaryAspectGraphNode,
        params: BaseParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
        context: Any,
    ) -> Any:
        """
        Shared primitive: invoke one regular or summary aspect callable only.

        Not for compensators, saga rollback, ``@on_error``, or non-aspect hooks.
        ``aspect_node`` is a regular or summary interchange graph node; wraps ``node_obj`` with scoped log / ``ContextView``.
        """
        aspect_log = ScopedLogger(
            coordinator=self._log_coordinator,
            nest_level=box.nested_level,
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
        action: BaseAction[Any, Any],
        aspect_node: RegularAspectGraphNode,
        params: BaseParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
        context: Any,
    ) -> tuple[BaseState, dict[str, Any], float]:
        """Execute one regular aspect with checker validation and state merge."""
        aspect_start = time.time()

        new_state_dict = await self.call_aspect(
            action=action,
            aspect_node=aspect_node,
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
        merged_state = BaseState(**{**state.to_dict(), **new_state_dict})

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
            raise MissingSummaryAspectError(
                f"{action_cls.__name__} has no summary aspect; declare @summary_aspect or use "
                "an action graph that exposes a summary interchange graph node.",
            )
        summary_start = time.time()
        raw = await self.call_aspect(
            action=action,
            aspect_node=summary_node,
            params=params,
            state=state,
            box=box,
            connections=connections,
            context=context,
        )
        ActionSchemaIntentResolver.resolve_result_type(action_cls)
        result = cast(BaseResult, raw)
        return result, (time.time() - summary_start)
