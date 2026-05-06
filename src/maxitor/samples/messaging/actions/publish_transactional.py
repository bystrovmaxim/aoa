# src/maxitor/samples/messaging/actions/publish_transactional.py
"""Полная поверхность декораторов в домене messaging."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from action_machine.context import Ctx
from action_machine.intents.aspects import regular_aspect, summary_aspect
from action_machine.intents.check_roles import check_roles
from action_machine.intents.checkers import result_string
from action_machine.intents.compensate import compensate
from action_machine.intents.connection import connection  # pylint: disable=no-name-in-module
from action_machine.intents.context_requires import context_requires
from action_machine.intents.depends import depends
from action_machine.intents.meta import meta
from action_machine.intents.on_error import on_error
from action_machine.logging import sensitive
from action_machine.model import BaseAction, BaseParams, BaseResult
from maxitor.samples.messaging.domain import MessagingDomain
from maxitor.samples.messaging.resources import MessagingDeadLetterStore, OutboxPrimaryDatabase
from maxitor.samples.messaging.resources.notification_gateway import NotificationGateway, NotificationGatewayResource
from maxitor.samples.messaging.resources.smtp_transport import SmtpTransportStub, SmtpTransportStubResource
from maxitor.samples.messaging.resources.webhook_fanout import WebhookFanoutStub, WebhookFanoutStubResource
from maxitor.samples.roles import EditorRole


@meta(description="Publish through outbox with full graph facets (messaging demo)", domain=MessagingDomain)
@check_roles(EditorRole)
@depends(
    NotificationGatewayResource,
    factory=lambda: NotificationGatewayResource(NotificationGateway()),
    description="In-app notifier",
)
@depends(
    SmtpTransportStubResource,
    factory=lambda: SmtpTransportStubResource(SmtpTransportStub()),
    description="SMTP transport",
)
@depends(
    WebhookFanoutStubResource,
    factory=lambda: WebhookFanoutStubResource(WebhookFanoutStub()),
    description="Webhook fan-out",
)
@connection(OutboxPrimaryDatabase, key="outbox_db", description="Outbox primary")
@connection(MessagingDeadLetterStore, key="dlq", description="DLQ store")
class PublishTransactionalOutboxAction(
    BaseAction["PublishTransactionalOutboxAction.Params", "PublishTransactionalOutboxAction.Result"],
):
    class Params(BaseParams):
        topic: str = Field(description="Logical topic")
        body: str = Field(description="Payload body")

        @property
        @sensitive(True, max_chars=3, char="*", max_percent=50)
        def routing_key_hint(self) -> str:
            """Sample logical routing-key fragment for demos; marked ``@sensitive`` so tooling masks it in logs."""
            return "rk-SECRET-MSG-DEMO"

    class Result(BaseResult):
        outbound_id: str = Field(description="Assigned outbound id")
        smtp_receipt: str = Field(description="SMTP stub receipt")
        status: str = Field(description="Publish status")

    @regular_aspect("Validate envelope")
    @result_string("validated_topic", required=True, min_length=1)
    @context_requires(Ctx.User.user_id)
    async def validate_envelope_aspect(
        self,
        params: PublishTransactionalOutboxAction.Params,
        state: Any,
        box: Any,
        connections: Any,
        ctx: Any,
    ) -> dict[str, Any]:
        return {"validated_topic": params.topic}

    @regular_aspect("Dispatch channels")
    @result_string("outbound_id", required=True, not_empty=True)
    @result_string("smtp_receipt", required=True, min_length=1)
    async def dispatch_aspect(
        self,
        params: PublishTransactionalOutboxAction.Params,
        state: Any,
        box: Any,
        connections: Any,
    ) -> dict[str, Any]:
        notifier = box.resolve(NotificationGatewayResource)
        await notifier.service.send(params.body)
        smtp = box.resolve(SmtpTransportStubResource)
        receipt = await smtp.service.send_raw("ops@example.com", params.body)
        oid = f"OB-{params.topic}-1"
        return {"outbound_id": oid, "smtp_receipt": receipt}

    @compensate("dispatch_aspect", "Best-effort undo publish")
    async def dispatch_compensate(
        self,
        params: PublishTransactionalOutboxAction.Params,
        state_before: Any,
        state_after: Any,
        box: Any,
        connections: Any,
        error: Exception,
    ) -> None:
        if state_after is not None:
            notifier = box.resolve(NotificationGatewayResource)
            await notifier.service.send(f"UNDO:{state_after.outbound_id}")

    @on_error(ValueError, description="Envelope validation failed")
    @context_requires(Ctx.User.user_id, Ctx.Request.trace_id)
    async def validation_error_on_error(
        self,
        params: PublishTransactionalOutboxAction.Params,
        state: Any,
        box: Any,
        connections: Any,
        error: ValueError,
        ctx: Any,
    ) -> PublishTransactionalOutboxAction.Result:
        return PublishTransactionalOutboxAction.Result(
            outbound_id="ERR",
            smtp_receipt="NONE",
            status="validation_failed",
        )

    @on_error(Exception, description="Messaging fallback")
    async def unexpected_error_on_error(
        self,
        params: PublishTransactionalOutboxAction.Params,
        state: Any,
        box: Any,
        connections: Any,
        error: Exception,
    ) -> PublishTransactionalOutboxAction.Result:
        return PublishTransactionalOutboxAction.Result(
            outbound_id="ERR",
            smtp_receipt="NONE",
            status="internal_error",
        )

    @summary_aspect("Build publish result")
    async def build_result_summary(
        self,
        params: PublishTransactionalOutboxAction.Params,
        state: Any,
        box: Any,
        connections: Any,
    ) -> PublishTransactionalOutboxAction.Result:
        return PublishTransactionalOutboxAction.Result(
            outbound_id=state.outbound_id,
            smtp_receipt=state.smtp_receipt,
            status="published",
        )
