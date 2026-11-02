# packages/aoa-action-machine/src/aoa/action_machine/runtime/method_box.py
"""
Method box — the one place a method of an action gets its own box.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Every method that receives ``box`` receives one of its own, carrying its own name and
the ``state`` its log may read. The action and method names of a log line then give
the id of that method's node in the graph (``<action>:<method>``).

The function is internal and is not a method of ``ToolsBox``, because the box is what
an action's author holds: an action must not be able to choose the name it logs under.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    AspectExecutor.call_aspect        (@regular_aspect, @summary_aspect)
    SagaCoordinator                   (@compensate)
    ErrorHandlerExecutor.handle       (@on_error)
    ActionProductMachine._decide      (@access_decide)
        │
        └── method_box(box, ..., method_name, state)
                ├── ScopedLogger(action, method_name, state, ...)
                └── ToolsBox(same tools as ``box``, log=that logger)

"""

from __future__ import annotations

from typing import Any

from aoa.action_machine.logging.domain_resolver import resolve_domain
from aoa.action_machine.logging.log_coordinator import LogCoordinator
from aoa.action_machine.logging.scoped_logger import ScopedLogger
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.runtime.tools_box import ToolsBox


def method_box(
    box: ToolsBox,
    *,
    coordinator: LogCoordinator,
    action: BaseAction[Any, Any],
    method_name: str,
    context: Any,
    state: BaseState,
    params: BaseParams | None,
) -> ToolsBox:
    """
    Return ``box`` with a logger of the method about to be called; nothing else differs.

    AI-CORE-BEGIN
    ROLE: The one place a method of an action gets its own ``ToolsBox``.
    CONTRACT: ``<action>:<method_name>`` of the returned box's log lines is the id of the method's graph node.
    INVARIANTS: Reads only ``run_child``, ``factory``, ``resources``, ``nested_level`` and ``rollup`` from ``box``.
    AI-CORE-END
    """
    log = ScopedLogger(
        coordinator=coordinator,
        nest_level=box.nested_level,
        action_name=action.get_full_class_name(),
        aspect_name=method_name,
        context=context,
        state=state,
        params=params,
        domain=resolve_domain(type(action)),
    )
    return ToolsBox(
        run_child=box.run_child,
        factory=box.factory,
        resources=box.resources,
        log=log,
        nested_level=box.nested_level,
        rollup=box.rollup,
    )
