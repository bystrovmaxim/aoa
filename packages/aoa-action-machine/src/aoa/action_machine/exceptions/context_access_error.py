# packages/aoa-action-machine/src/aoa/action_machine/exceptions/context_access_error.py
"""ContextAccessError."""


class ContextAccessError(Exception):
    """
    Access attempt to a context field not declared in ``@context_requires``.
    """

    def __init__(self, key: str, allowed_keys: frozenset[str]) -> None:
        """Initialize context access violation details."""
        self.key: str = key
        self.allowed_keys: frozenset[str] = allowed_keys
        super().__init__(
            f"Access to context field '{key}' is forbidden. "
            f"Allowed fields: {sorted(allowed_keys)}. "
            f"Add '{key}' to the aspect's @context_requires decorator."
        )
