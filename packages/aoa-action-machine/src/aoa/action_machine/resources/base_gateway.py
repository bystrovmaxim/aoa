# packages/aoa-action-machine/src/aoa/action_machine/resources/base_gateway.py
"""
Marker base class for external service gateway resources.

═══════════════════════════════════════════════════════════════════════════════
ROLE
═══════════════════════════════════════════════════════════════════════════════

``BaseGateway`` is the root for resources that delegate work to external
services — payment processors, notification providers, fraud-check APIs,
and any third-party service the process calls but does not own.

The process issues a request and receives a response. It does not know (or
need to know) how the service handles the work internally.

═══════════════════════════════════════════════════════════════════════════════
SCOPE (IN / OUT)
═══════════════════════════════════════════════════════════════════════════════

**In scope**
    Stripe, SendGrid, Twilio, fraud-check APIs, any external service call.

**Out of scope**
    External data stores you read/write directly (→ ``BaseStorage``).
    Internal engines you create and own (→ ``BaseController``).
"""

from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.resources.base_resource import BaseResource


@exclude_graph_model
class BaseGateway(BaseResource):
    """
    AI-CORE-BEGIN
        ROLE: Root for resources that delegate work to external services.
        CONTRACT: Do not assume the service retains state between calls.
        INVARIANTS: You do not know how the service works internally.
    AI-CORE-END
    """
