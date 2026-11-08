# packages/aoa-demo/src/aoa/demo/model/messaging/resources/outbox_primary_database_storage.py
"""
OutboxPrimaryDatabaseStorage — database-free demo storage with SQL lifecycle semantics.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Represent the domain's storage in the demo without opening a database connection.
The SQL lifecycle methods are harmless no-ops; inherited close remains safe.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    Domain actions and entities -> OutboxPrimaryDatabaseStorage -> SqlStorage contract
"""

from aoa.action_machine.intents.entities import entities
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.sql import SqlStorage
from aoa.demo.model.messaging.entities.msg_batching_fence import BatchingFenceCoreEntity
from aoa.demo.model.messaging.entities.msg_courier_attempt_ledger import CourierAttemptLedgerCoreEntity
from aoa.demo.model.messaging.entities.msg_dedupe_correlation import DedupeCorrelationCoreEntity
from aoa.demo.model.messaging.entities.msg_dispatcher_cursor_shard import DispatcherCursorShardCoreEntity
from aoa.demo.model.messaging.entities.msg_downstream_watermark import DownstreamWatermarkCoreEntity
from aoa.demo.model.messaging.entities.msg_er_cycle_triangle_stub import (
    MsgDirectedCycleTriangleACoreEntity,
    MsgDirectedCycleTriangleBCoreEntity,
    MsgDirectedCycleTriangleCCoreEntity,
)
from aoa.demo.model.messaging.entities.msg_fanout_replay_cursor import FanoutReplayCursorCoreEntity
from aoa.demo.model.messaging.entities.msg_hop_latency_sample import HopLatencySampleCoreEntity
from aoa.demo.model.messaging.entities.msg_mesh_courier_replay import MsgCourierReplayCorrelateCoreEntity
from aoa.demo.model.messaging.entities.msg_mesh_outbox_webhook import MsgOutboxWebhookCorrelateCoreEntity
from aoa.demo.model.messaging.entities.msg_replay_ticket import ReplayTicketCoreEntity
from aoa.demo.model.messaging.entities.msg_throttle_lease import ThrottleLeaseCoreEntity
from aoa.demo.model.messaging.entities.msg_webhook_ingress_receipt import WebhookIngressReceiptCoreEntity
from aoa.demo.model.messaging.entities.msg_webhook_signature_envelope import WebhookSignatureEnvelopeCoreEntity
from aoa.demo.model.messaging.entities.outbox_message import OutboxMessageCoreEntity


@meta(description="Transactional outbox primary DB (stub)")
@entities(
    BatchingFenceCoreEntity,
    CourierAttemptLedgerCoreEntity,
    DedupeCorrelationCoreEntity,
    DispatcherCursorShardCoreEntity,
    DownstreamWatermarkCoreEntity,
    MsgDirectedCycleTriangleACoreEntity,
    MsgDirectedCycleTriangleBCoreEntity,
    MsgDirectedCycleTriangleCCoreEntity,
    FanoutReplayCursorCoreEntity,
    HopLatencySampleCoreEntity,
    MsgCourierReplayCorrelateCoreEntity,
    MsgOutboxWebhookCorrelateCoreEntity,
    ReplayTicketCoreEntity,
    ThrottleLeaseCoreEntity,
    WebhookIngressReceiptCoreEntity,
    WebhookSignatureEnvelopeCoreEntity,
    OutboxMessageCoreEntity,
)
class OutboxPrimaryDatabaseStorage(SqlStorage):
    """
    AI-CORE-BEGIN
    ROLE: Database-free storage for the demo domain.
    CONTRACT: Provide the SQL lifecycle without acquiring a connection.
    INVARIANTS: The class retains its Storage kind and domain metadata.
    AI-CORE-END
    """

    def __init__(self, rollup: bool = False) -> None:
        """Preserve the SQL contract’s rollup configuration."""
        super().__init__(rollup=rollup)

    async def open(self) -> None:
        """Keep the database-free store ready for use."""
        return None

    async def begin(self) -> None:
        """Accept a transaction boundary without external state."""
        return None

    async def commit(self) -> None:
        """Finish the demo transaction without persistence."""
        return None

    async def rollback(self) -> None:
        """Finish the demo transaction without external writes."""
        return None
