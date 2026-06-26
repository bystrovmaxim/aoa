# packages/aoa-langgraph/src/aoa/langgraph/exceptions.py
"""
Exceptions for the ``aoa-langgraph`` package.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

All public exception types raised by ``LangGraphController``,
``LangGraphAdapter``, and ``AgentState``. Import from ``aoa.langgraph``
directly — these are part of the public API.

═══════════════════════════════════════════════════════════════════════════════
EXCEPTION MAP
═══════════════════════════════════════════════════════════════════════════════

Controller field declaration (raised immediately at declaration time):

    DuplicateFieldError          — same name declared twice via .inp()/.mid()/.out()
    MissingFieldDescriptionError — .inp() or .mid() called without a description
    ControllerAlreadyBuiltError  — fluent method called after .build()

State access (raised at node runtime):

    FieldNotReadyError           — node reads an UNSET mid-field via AgentState[key]

Adapter topology (raised at build / ainvoke time):

    UnregisteredNodeError        — edge references a node never registered
    MissingConnectionError       — Action requires a connection absent from pool
    RouteKeyError                — .route() on() returned a key not in paths
    StateFieldMismatchError      — Action Result field absent from AgentState

"""


class DuplicateFieldError(Exception):
    """Raised when a field name is declared more than once across .inp()/.mid()/.out()."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Field '{name}' is already declared.")


class ControllerAlreadyBuiltError(Exception):
    """Raised when a fluent method is called after .build()."""


class FieldNotReadyError(Exception):
    """Raised when a node reads an UNSET mid-field via AgentState.__getitem__."""

    def __init__(self, field_name: str) -> None:
        self.field_name = field_name
        super().__init__(f"Field '{field_name}' has not been produced yet (value is UNSET).")


class MissingFieldDescriptionError(Exception):
    """Raised when .inp() or .mid() is called without a description."""

    def __init__(self, field_name: str) -> None:
        self.field_name = field_name
        super().__init__(
            f"Field '{field_name}' declared without a description. "
            f"Pass it as the third positional argument: .inp('{field_name}', type, 'description')."
        )


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
