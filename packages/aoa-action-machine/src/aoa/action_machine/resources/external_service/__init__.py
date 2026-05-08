# packages/aoa-action-machine/src/aoa/action_machine/resources/external_service/__init__.py
"""Resource managers for typed external service clients."""

from aoa.action_machine.resources.external_service.external_service_resource import (
    ExternalServiceResource,
)
from aoa.action_machine.resources.external_service.protocol_external_service_resource import (
    ProtocolExternalServiceResource,
)
from aoa.action_machine.resources.external_service.wrapper_external_service_resource import (
    WrapperExternalServiceResource,
)

__all__ = [
    "ExternalServiceResource",
    "ProtocolExternalServiceResource",
    "WrapperExternalServiceResource",
]
