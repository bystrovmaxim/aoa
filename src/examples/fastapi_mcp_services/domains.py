# src/examples/fastapi_mcp_services/domains.py
"""
Business domains for the FastAPI + MCP example service.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Domains are typed markers that group actions by business area. Each domain is a
``BaseDomain`` subclass with a unique ``name`` string. The coordinator graph
can surface domain nodes so tooling and docs reflect boundaries between order
flows and system utilities.

This module defines:

- ``OrdersDomain`` — create/get order actions.
- ``SystemDomain`` — cross-cutting utilities (e.g. ping).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    @meta(..., domain=OrdersDomain | SystemDomain)
              |
              v
         GraphCoordinator graph
              |
              +-- domain nodes (class_ref -> OrdersDomain / SystemDomain)
              |
              +-- action nodes linked to domain metadata

    Example actions using these domains live under ``actions/`` and are wired
    by FastAPI and MCP adapters without duplicating domain definitions.

"""

from action_machine.domain.base_domain import BaseDomain


class OrdersDomain(BaseDomain):
    """Order lifecycle actions (create, fetch, etc.)."""

    name = "orders"


class SystemDomain(BaseDomain):
    """System-level utilities (e.g. liveness ping)."""

    name = "system"
