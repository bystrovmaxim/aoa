# src/maxitor/samples/inventory/domain.py
"""Bounded-context marker for synthetic inventory / fulfillment graph demo."""

from action_machine.domain import BaseDomain


class InventoryDomain(BaseDomain):
    name = "inventory"
    description = "Synthetic inventory chain + correlation hub for heterogeneous ERD demos"
