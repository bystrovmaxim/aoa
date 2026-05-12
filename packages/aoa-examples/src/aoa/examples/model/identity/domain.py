# packages/aoa-examples/src/aoa/examples/model/identity/domain.py
"""Bounded-context marker for identity primitives (dense tiny mesh demo)."""

from aoa.action_machine.domain import BaseDomain


class IdentityDomain(BaseDomain):
    name = "identity"
    description = "Synthetic identity/account slice for heterogeneous ERD cardinality"
