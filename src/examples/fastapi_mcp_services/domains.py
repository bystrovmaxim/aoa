# src/examples/fastapi_mcp_services/domains.py
"""
Business domains for the FastAPI service example.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Domains are typed markers of actions' belonging to business areas.
Each domain is a class inheriting from BaseDomain, with a unique string
name. Domains appear in the GateCoordinator graph as separate nodes,
allowing visualization of the architecture by business areas.

This example defines two domains:
- OrdersDomain — actions related to orders.
- SystemDomain — system actions (ping, health check).
"""

from action_machine.domain.base_domain import BaseDomain


class OrdersDomain(BaseDomain):
    """Orders domain. Combines actions for creating, retrieving, and managing orders."""
    name = "orders"


class SystemDomain(BaseDomain):
    """System domain. Combines utility actions: ping, monitoring."""
    name = "system"
