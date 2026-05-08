# src/action_machine/exceptions/cyclic_dependency_error.py
"""CyclicDependencyError."""


class CyclicDependencyError(Exception):
    """
    Dependency graph became cyclic during edge insertion.
    """
