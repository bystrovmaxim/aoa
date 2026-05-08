# packages/aoa-action-machine/src/aoa/action_machine/resources/external_service/external_service_resource.py
"""
ExternalServiceResource — generic holder for typed external service clients.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provides a ``BaseResource`` that wraps exactly one runtime service client
(API client, SDK handle, messaging producer, etc.). The type parameter pins the
service interface so aspects can treat ``connections["…"]`` as typed access to
``.service``.

Nested actions receive ``WrapperExternalServiceResource`` instances that delegate
the same ``service`` reference and rollup policy.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    ConcreteClient   – user-defined type
         │
         ▼ __init__(service)
    ExternalServiceResource[ConcreteClient]
         │
         └── .service  → client reference

    ToolsBox.run → WrapperExternalServiceResource(inner)
         │
         └── delegates .service / check_rollup_support

"""

from abc import ABC

from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.resources.external_service.protocol_external_service_resource import (
    ProtocolExternalServiceResource,
)
from aoa.action_machine.resources.external_service.wrapper_external_service_resource import (
    WrapperExternalServiceResource,
)
from aoa.graph.exclude_graph_model import exclude_graph_model


@exclude_graph_model
class ExternalServiceResource[TService](BaseResource, ProtocolExternalServiceResource, ABC):
    """
AI-CORE-BEGIN
    ROLE: Resource manager exposing a single typed external service reference.
    CONTRACT: ``service`` holds the injected client; nested actions use WrapperExternalServiceResource.
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

    def get_wrapper_class(self) -> type[BaseResource] | None:
        """Return proxy used when this manager is propagated to child actions."""
        return WrapperExternalServiceResource
