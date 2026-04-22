# src/action_machine/resources/external_service/external_service_manager.py
"""
ExternalServiceManager — generic holder for typed external service clients.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provides a ``BaseResourceManager`` that wraps exactly one runtime service client
(API client, SDK handle, messaging producer, etc.). The type parameter pins the
service interface so aspects can treat ``connections["…"]`` as typed access to
``.service``.

Nested actions receive ``WrapperExternalServiceManager`` instances that delegate
the same ``service`` reference and rollup policy.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    ConcreteClient   – user-defined type
         │
         ▼ __init__(service)
    ExternalServiceManager[ConcreteClient]
         │
         └── .service  → client reference

    ToolsBox.run → WrapperExternalServiceManager(inner)
         │
         └── delegates .service / check_rollup_support

"""

from action_machine.resources.base_resource_manager import BaseResourceManager
from action_machine.resources.external_service.protocol_external_service_manager import (
    ProtocolExternalServiceManager,
)
from action_machine.resources.external_service.wrapper_external_service_manager import (
    WrapperExternalServiceManager,
)


class ExternalServiceManager[TService](BaseResourceManager, ProtocolExternalServiceManager):
    """
AI-CORE-BEGIN
    ROLE: Resource manager exposing a single typed external service reference.
    CONTRACT: ``service`` holds the injected client; nested actions use WrapperExternalServiceManager.
    INVARIANTS: Generic parameter matches the runtime type stored in ``_service``.
AI-CORE-END
"""

    _service: TService

    def __init__(self, service: TService) -> None:
        """Store the injected service client."""
        self._service = service

    @property
    def service(self) -> TService:
        """Runtime client passed into aspects via ``connections``."""
        return self._service

    def check_rollup_support(self) -> bool:
        """External clients are not transactional SQL-style rollup targets."""
        return False

    def get_wrapper_class(self) -> type[BaseResourceManager] | None:
        """Return proxy used when this manager is propagated to child actions."""
        return WrapperExternalServiceManager
