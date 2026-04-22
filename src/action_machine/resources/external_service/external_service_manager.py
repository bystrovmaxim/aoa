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

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    ConcreteClient   – user-defined protocol or concrete class
         │
         ▼ __init__(service)
    ExternalServiceManager[ConcreteClient]
         │
         └── .service  → passed-through client reference

"""


from action_machine.resources.base_resource_manager import BaseResourceManager


class ExternalServiceManager[TService](BaseResourceManager):
    """
AI-CORE-BEGIN
    ROLE: Resource manager exposing a single typed external service reference.
    CONTRACT: ``service`` holds the injected client; ``get_wrapper_class`` defaults to None.
    INVARIANTS: Generic parameter matches the runtime type stored in ``service``.
AI-CORE-END
"""

    service: TService

    def __init__(self, service: TService) -> None:
        """Store the injected service client."""
        self.service = service

    def get_wrapper_class(self) -> type["BaseResourceManager"] | None:
        """Nested actions reuse the same manager surface; no proxy wrapper."""
        return None
