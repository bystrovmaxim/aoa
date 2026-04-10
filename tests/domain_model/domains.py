# tests/domain_model/domains.py
"""
Business domains for the test domain model.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Defines business domains used in test Actions. Domains are typed markers
of an action's belonging to a business area. Each domain is a class
inheriting from BaseDomain, with a unique string name in the name attribute.

═══════════════════════════════════════════════════════════════════════════════
DOMAINS
═══════════════════════════════════════════════════════════════════════════════

- OrdersDomain — orders domain. Used in FullAction, SimpleAction.
- SystemDomain — system domain. Used in PingAction, ChildAction.

═══════════════════════════════════════════════════════════════════════════════
USAGE IN TESTS
═══════════════════════════════════════════════════════════════════════════════

Domains are passed to the @meta(domain=...) decorator when declaring an Action:

    @meta(description="Create an order", domain=OrdersDomain)
    class FullAction(BaseAction[...]): ...

Domains appear in the GateCoordinator graph as "domain" type nodes with
"belongs_to" edges from Action to domain.
"""

from action_machine.domain.base_domain import BaseDomain


class OrdersDomain(BaseDomain):
    """Orders domain — used for actions related to order processing."""
    name = "orders"
    description = "Domain for processing customer orders"


class SystemDomain(BaseDomain):
    """System domain — used for infrastructure actions (ping, health check)."""
    name = "system"
    description = "System domain for infrastructure operations"
