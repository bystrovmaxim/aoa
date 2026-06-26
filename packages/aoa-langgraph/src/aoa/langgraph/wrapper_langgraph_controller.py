# packages/aoa-langgraph/src/aoa/langgraph/wrapper_langgraph_controller.py
"""
WrapperLangGraphController — thin proxy for child actions.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Installed by ``ToolsBox.run`` when propagating ``connections`` to nested actions.
Exposes only ``ainvoke()`` — builder methods (``.inp()``, ``.mid()``,
``.build()``, etc.) are not forwarded, so child actions cannot mutate the
graph that the owning action constructed.

``check_rollup_support`` and ``get_wrapper_class`` delegate to the inner
controller so that the wrapper behaves identically at every nesting level.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    LangGraphController (owner action)
        │
        └── WrapperLangGraphController
                ainvoke(data, box)       → delegates to inner  [added PR06]
                check_rollup_support()   → delegates to inner
                get_wrapper_class()      → WrapperLangGraphController

"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.resources.base_controller import BaseController
from aoa.action_machine.resources.base_resource import BaseResource

if TYPE_CHECKING:
    from aoa.action_machine.runtime.tools_box import ToolsBox
    from aoa.langgraph.controller import LangGraphController


@exclude_graph_model
class WrapperLangGraphController(BaseController):
    """
    AI-CORE-BEGIN
        ROLE: Proxy of LangGraphController for child actions; exposes ainvoke() only.
        CONTRACT: Wraps a built controller; builder methods are not forwarded.
        INVARIANTS: _inner is always a fully built LangGraphController (_built=True).
    AI-CORE-END
    """

    def __init__(self, inner: LangGraphController) -> None:
        """Wrap a fully built LangGraphController for child-action propagation."""
        self._inner = inner

    async def ainvoke(self, data: dict[str, Any], box: ToolsBox) -> dict[str, Any]:
        """Delegate ainvoke to the wrapped controller; child actions cannot call build/compile."""
        return await self._inner.ainvoke(data, box)

    async def check_rollup_support(self) -> bool:
        """Delegate to the wrapped controller."""
        return await self._inner.check_rollup_support()

    def get_wrapper_class(self) -> type[BaseResource] | None:
        """Return this wrapper class so deeper nesting levels are also wrapped."""
        return WrapperLangGraphController
