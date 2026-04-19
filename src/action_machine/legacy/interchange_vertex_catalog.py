# src/action_machine/legacy/interchange_vertex_catalog.py
"""
Known interchange ``node_type`` strings for the default ActionMachine inspector set.

This is a **documentation / contract / test** catalog only. The
:mod:`graph` package does not import it; graph algorithms treat
``node_type`` as opaque strings from inspectors.
"""

from __future__ import annotations

from typing import Final

INTERCHANGE_KNOWN_VERTEX_TYPES: Final[frozenset[str]] = frozenset(
    {
        "Action",
        "RegularAspect",
        "SummaryAspect",
        "Compensator",
        "error_handler",
        "Checker",
        "sensitive_field",
        "role_class",
        "Application",
        "Domain",
        "Entity",
        "lifecycle",
        "lifecycle_state_initial",
        "lifecycle_state_intermediate",
        "lifecycle_state_final",
        "params_schema",
        "result_schema",
        "service",
        "resource_manager",
        "plugin",
        "subscription",
    },
)
