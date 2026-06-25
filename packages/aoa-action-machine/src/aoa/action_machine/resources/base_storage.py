# packages/aoa-action-machine/src/aoa/action_machine/resources/base_storage.py
"""
Marker base class for external data storage resources.

═══════════════════════════════════════════════════════════════════════════════
ROLE
═══════════════════════════════════════════════════════════════════════════════

``BaseStorage`` is the root for resources that connect to external data stores —
databases, caches, message queues. The data exists independently of the process:
it was there before the process started and will remain after it stops.

The process only reads and writes. It does not own the data's lifecycle.

═══════════════════════════════════════════════════════════════════════════════
SCOPE (IN / OUT)
═══════════════════════════════════════════════════════════════════════════════

**In scope**
    PostgreSQL, Redis, Kafka, S3, any external store.

**Out of scope**
    External services you delegate work to (→ ``BaseGateway``).
    Internal engines you create and own (→ ``BaseController``).
"""

from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.resources.base_resource import BaseResource


@exclude_graph_model
class BaseStorage(BaseResource):
    """
    AI-CORE-BEGIN
        ROLE: Root for resources that connect to external data stores.
        CONTRACT: Connect, read, write; do not manage the data's lifecycle.
        INVARIANTS: The data existed before the process and will remain after.
    AI-CORE-END
    """
