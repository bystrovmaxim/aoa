# src/action_machine/resources/external_service/wrapper_external_service_resource.py
"""
Wrapper for external-service managers passed into nested actions.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``WrapperExternalServiceResource`` wraps any ``ProtocolExternalServiceResource``.
It is installed when ``ToolsBox.run`` propagates ``connections`` to child actions.
There is no SQL-style lifecycle to block; the wrapper **delegates** ``service``
and ``check_rollup_support`` so nested code sees the same client and rollup
policy as the owner manager.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    ProtocolExternalServiceResource (owner)
        │
        └── WrapperExternalServiceResource
                service              -> delegates to inner
                check_rollup_support -> delegates to inner

"""

from typing import Any

from action_machine.resources.base_resource import BaseResource
from action_machine.resources.external_service.protocol_external_service_resource import (
    ProtocolExternalServiceResource,
)


class WrapperExternalServiceResource(BaseResource, ProtocolExternalServiceResource):
    """
    Thin proxy for nested actions using the same external client handle.

    Delegates ``service`` and rollup capability checks to the wrapped manager.
    """

    def __init__(self, inner: ProtocolExternalServiceResource) -> None:
        """Hold reference to the manager created by the owning action."""
        self._inner = inner

    @property
    def service(self) -> Any:
        """Delegate to the wrapped manager."""
        return self._inner.service

    def check_rollup_support(self) -> bool:
        """Delegate to the wrapped manager."""
        return self._inner.check_rollup_support()

    def get_wrapper_class(self) -> type[BaseResource] | None:
        """Return wrapper type for deeper nesting levels."""
        return WrapperExternalServiceResource
