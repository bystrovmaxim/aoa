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

build() validation (raised by .build()):

    NoOutputFieldsError          — no output fields declared (global or per-finish)
    UndeclaredOutputFieldError   — out field not declared in .inp() or .mid()
    InconsistentFinishOutputError — some finish nodes have explicit outs, others do not

compile() / runtime (raised by .compile() or during graph execution):

    CompileBeforeBuildError      — .compile() called before .build()
    UnexpectedResultFieldError   — Action returns a field not declared in AgentState

ainvoke() (raised by .ainvoke()):

    MissingInputFieldError       — required inp-field absent from the input dict

topology validation (raised by .build()):

    NoNodesError             — no nodes registered via .node()
    NoEntryPointError        — no .start() declared
    NoFinishPointError       — no .finish() declared
    DeadEndNodeError         — non-finish node has no outgoing edges
    FinishUnreachableError   — finish node unreachable from all start nodes
    UnreachableNodeError     — node unreachable from all start nodes
    FieldHasNoProducerError  — required Params field has no producer in the graph
    OutputHasNoProducerError — out-field has no producer in the graph

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


class NoOutputFieldsError(Exception):
    """Raised by .build() when no output fields are declared (global or per-finish)."""


class UndeclaredOutputFieldError(Exception):
    """Raised by .build() when an out field is not declared in .inp() or .mid()."""

    def __init__(self, field_name: str) -> None:
        self.field_name = field_name
        super().__init__(
            f"Output field '{field_name}' is not declared in .inp() or .mid()."
        )


class InconsistentFinishOutputError(Exception):
    """Raised by .build() when some finish nodes have explicit out fields and others do not."""

    def __init__(self, with_outs: list[str], without_outs: list[str]) -> None:
        self.with_outs = with_outs
        self.without_outs = without_outs
        super().__init__(
            f"Finish nodes {with_outs} declare explicit out fields, "
            f"but {without_outs} do not. Either all finishes must declare out fields "
            f"or none of them should (use global .out() instead)."
        )


class CompileBeforeBuildError(Exception):
    """Raised when .compile() is called before .build()."""


class UnexpectedResultFieldError(Exception):
    """Raised when an Action returns a result field not declared in AgentState."""

    def __init__(self, action_cls: type, unexpected: list[str]) -> None:
        """Store the offending class and field list for programmatic inspection."""
        self.action_cls = action_cls
        self.unexpected = unexpected
        super().__init__(
            f"{action_cls.__name__} returned fields not declared in AgentState: "
            f"{unexpected}. Add them to .mid() or .inp() declarations."
        )


class MissingInputFieldError(Exception):
    """Raised by .ainvoke() when a required inp-field is absent from the input dict."""

    def __init__(self, field_name: str) -> None:
        """Store the missing field name for programmatic inspection."""
        self.field_name = field_name
        super().__init__(
            f"Required inp-field '{field_name}' is missing from the dict passed to .ainvoke()."
        )


class NoNodesError(Exception):
    """Raised by .build() when no nodes have been registered via .node()."""


class NoEntryPointError(Exception):
    """Raised by .build() when no .start() has been called."""


class NoFinishPointError(Exception):
    """Raised by .build() when no .finish() has been called."""


class DeadEndNodeError(Exception):
    """Raised by .build() when a non-finish node has no outgoing edges."""

    def __init__(self, node_name: str) -> None:
        """Store the offending node name for programmatic inspection."""
        self.node_name = node_name
        super().__init__(
            f"Node '{node_name}' is a dead end — add an outgoing edge or declare it a finish node."
        )


class FinishUnreachableError(Exception):
    """Raised by .build() when a finish node cannot be reached from any start node."""

    def __init__(self, node_name: str) -> None:
        """Store the unreachable finish node name for programmatic inspection."""
        self.node_name = node_name
        super().__init__(f"Finish node '{node_name}' is unreachable from all start nodes.")


class UnreachableNodeError(Exception):
    """Raised by .build() when a node cannot be reached from any start node."""

    def __init__(self, node_name: str) -> None:
        """Store the unreachable node name for programmatic inspection."""
        self.node_name = node_name
        super().__init__(f"Node '{node_name}' is unreachable from all start nodes.")


class FieldHasNoProducerError(Exception):
    """Raised by .build() when a required Params field has no producer anywhere in the graph."""

    def __init__(self, node_name: str, field_name: str) -> None:
        """Store the consuming node name and the field name for programmatic inspection."""
        self.node_name = node_name
        self.field_name = field_name
        super().__init__(
            f"Node '{node_name}': required Params field '{field_name}' has no producer "
            "in the graph and is not declared as an inp-field."
        )


class OutputHasNoProducerError(Exception):
    """Raised by .build() when an out-field has no producer anywhere in the graph."""

    def __init__(self, field_name: str) -> None:
        """Store the field name for programmatic inspection."""
        self.field_name = field_name
        super().__init__(
            f"Out-field '{field_name}' has no producer in the graph "
            "and is not declared as an inp-field."
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
