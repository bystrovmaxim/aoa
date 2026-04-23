# src/action_machine/resources/external_service/protocol_external_service_resource.py
# pylint: disable=unnecessary-ellipsis  # Protocol member bodies use ellipsis per PEP 544 stubs.
"""
ProtocolExternalServiceResource — typed surface for external client holders.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Minimal contract for resource managers that expose a single ``service`` handle
(API client, SDK, producer, …) and participate in rollup capability checks like
other ``BaseResource`` implementations.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    ProtocolExternalServiceResource (typing.Protocol)
              │
              △ nominal / structural match
              │
    ExternalServiceResource / WrapperExternalServiceResource

"""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ProtocolExternalServiceResource(Protocol):
    """
AI-CORE-BEGIN
    ROLE: Typed contract for managers that expose one external client reference.
    CONTRACT: ``service`` accessor and ``check_rollup_support`` per BaseResource.
    INVARIANTS: Structural subtyping for concrete and wrapper implementations.
AI-CORE-END
"""

    @property
    def service(self) -> Any:
        """Runtime client instance passed into aspects via ``connections``."""
        ...

    def check_rollup_support(self) -> bool:
        """Same meaning as ``BaseResource.check_rollup_support``."""
        ...
