# src/maxitor/samples/identity/domain.py
"""Bounded-context marker for identity primitives (dense tiny mesh demo)."""

from action_machine.domain import BaseDomain


class IdentityDomain(BaseDomain):
    name = "identity"
    description = "Synthetic identity/account slice for heterogeneous ERD cardinality"
