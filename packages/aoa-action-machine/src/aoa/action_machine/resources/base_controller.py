# packages/aoa-action-machine/src/aoa/action_machine/resources/base_controller.py
"""
Marker base class for internal long-lived controller resources.

═══════════════════════════════════════════════════════════════════════════════
ROLE
═══════════════════════════════════════════════════════════════════════════════

``BaseController`` is the root for internal long-lived dependencies whose
lifecycle the process fully owns — compiled LangGraph graphs, in-memory rule
engines, wrappers over legacy subsystems.

The key distinction: you instantiated this object, you initialise it, and you
shut it down. It does not exist outside the process.

═══════════════════════════════════════════════════════════════════════════════
SCOPE (IN / OUT)
═══════════════════════════════════════════════════════════════════════════════

**In scope**
    Compiled LangGraph graphs, in-memory engines, legacy code wrappers.

**Out of scope**
    External data stores (→ ``BaseStorage``).
    External services you call but do not own (→ ``BaseGateway``).
"""

from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.resources.base_resource import BaseResource


@exclude_graph_model
class BaseController(BaseResource):
    """
    AI-CORE-BEGIN
        ROLE: Root for internal resources whose lifecycle the process owns.
        CONTRACT: You create it, initialise it, and shut it down.
        INVARIANTS: Lives only as long as the process; does not persist on its own.
    AI-CORE-END
    """
