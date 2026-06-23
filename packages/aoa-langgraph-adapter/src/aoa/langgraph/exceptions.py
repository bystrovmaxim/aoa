class UnregisteredNodeError(Exception):
    """Raised when an edge references a node not registered via .node()."""


class MissingConnectionError(Exception):
    """Raised at .compile() when an Action requires a connection absent from the pool."""


class RouteKeyError(Exception):
    """Raised during graph execution when .route() on() returns a key absent from paths."""


class StateFieldMismatchError(ValueError):
    """Raised at .compile() when an Action Result contains fields absent from AgentState."""

    def __init__(self, action_name: str, missing_fields: list[str], state_class: str) -> None:
        self.action_name = action_name
        self.missing_fields = missing_fields
        self.state_class = state_class
        super().__init__(
            f"Action '{action_name}' returns fields not declared in AgentState '{state_class}': "
            f"{', '.join(missing_fields)}. "
            f"Add these fields to the AgentState class, or use response_mapper to map them."
        )
