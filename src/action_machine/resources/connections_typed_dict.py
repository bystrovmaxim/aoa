# src/action_machine/resources/connections_typed_dict.py
"""
Base TypedDict contract for ``connections`` mapping passed into aspects.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``Connections`` defines a minimal static typing contract for resource managers
in action aspect signatures. The default key ``"connection"`` covers the most
common single-resource case; multi-resource actions can extend this TypedDict.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    @connection declarations on action class
                 |
                 v
    Runtime builds validated connections payload (dict)
                 |
                 +--> Aspect signature typing: Connections / subclass
                 |
                 v
    Aspect reads managers by keys (e.g. connections["connection"])

"""

from typing import TypedDict

from action_machine.resources.base_resource_manager import BaseResourceManager


class Connections(TypedDict, total=False):
    """
    Base TypedDict for action ``connections`` mapping.

    Includes standard ``connection`` key for common single-resource scenarios.
    """

    connection: BaseResourceManager
