# packages/aoa-examples/src/aoa/examples/model/messaging/actions/__init__.py
from aoa.examples.model.messaging.actions.drain_dlq_stub import DrainDlqStubAction
from aoa.examples.model.messaging.actions.publish_transactional import PublishTransactionalOutboxAction
from aoa.examples.model.messaging.actions.queue_depth_probe import QueueDepthProbeAction
from aoa.examples.model.messaging.actions.template_render_stub import TemplateRenderStubAction

DrainDlqStubParams = DrainDlqStubAction.Params
DrainDlqStubResult = DrainDlqStubAction.Result
PublishTransactionalOutboxParams = PublishTransactionalOutboxAction.Params
PublishTransactionalOutboxResult = PublishTransactionalOutboxAction.Result
QueueDepthProbeParams = QueueDepthProbeAction.Params
QueueDepthProbeResult = QueueDepthProbeAction.Result
TemplateRenderStubParams = TemplateRenderStubAction.Params
TemplateRenderStubResult = TemplateRenderStubAction.Result

__all__ = [
    "DrainDlqStubAction",
    "DrainDlqStubParams",
    "DrainDlqStubResult",
    "PublishTransactionalOutboxAction",
    "PublishTransactionalOutboxParams",
    "PublishTransactionalOutboxResult",
    "QueueDepthProbeAction",
    "QueueDepthProbeParams",
    "QueueDepthProbeResult",
    "TemplateRenderStubAction",
    "TemplateRenderStubParams",
    "TemplateRenderStubResult",
]
