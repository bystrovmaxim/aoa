# packages/aoa-maxitor/src/aoa/maxitor/samples/messaging/actions/__init__.py
from aoa.maxitor.samples.messaging.actions.drain_dlq_stub import DrainDlqStubAction
from aoa.maxitor.samples.messaging.actions.publish_transactional import PublishTransactionalOutboxAction
from aoa.maxitor.samples.messaging.actions.queue_depth_probe import QueueDepthProbeAction
from aoa.maxitor.samples.messaging.actions.template_render_stub import TemplateRenderStubAction

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
