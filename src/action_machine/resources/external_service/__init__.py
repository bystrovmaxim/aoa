# src/action_machine/resources/external_service/__init__.py
"""Resource managers for typed external service clients."""

from action_machine.resources.external_service.external_service_manager import (
    ExternalServiceManager,
)
from action_machine.resources.external_service.protocol_external_service_manager import (
    ProtocolExternalServiceManager,
)
from action_machine.resources.external_service.wrapper_external_service_manager import (
    WrapperExternalServiceManager,
)

__all__ = [
    "ExternalServiceManager",
    "ProtocolExternalServiceManager",
    "WrapperExternalServiceManager",
]
