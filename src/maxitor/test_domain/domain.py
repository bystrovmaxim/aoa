# src/maxitor/test_domain/domain.py
"""
TestDomain — bounded-context marker for synthetic test graph.

AI-CORE-BEGIN
ROLE: Domain marker grouping all test facets under one bounded context.
CONTRACT: BaseDomain subclass with fixed name and description.
INVARIANTS: name == "test"; class name ends with Domain.
NEIGHBORS: Referenced by @meta and @entity decorators in test_domain submodules.
AI-CORE-END
"""

from action_machine.domain.base_domain import BaseDomain


class TestDomain(BaseDomain):
    """
    AI-CORE-BEGIN
    ROLE: Typed bounded-context marker for the synthetic test graph.
    CONTRACT: Class-level name / description only; instances are not used.
    INVARIANTS: name == "test"; non-empty description.
    NEIGHBORS: All test entities and actions declare domain=TestDomain.
    AI-CORE-END
    """

    name = "test"
    description = "Synthetic domain for full ActionMachine graph coverage"
