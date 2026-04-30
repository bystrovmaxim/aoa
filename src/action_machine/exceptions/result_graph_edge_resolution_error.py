# src/action_machine/exceptions/result_graph_edge_resolution_error.py
"""ResultGraphEdgeResolutionError."""


from __future__ import annotations

from action_machine.exceptions.graph_edge_resolution_error import GraphEdgeResolutionError


class ResultGraphEdgeResolutionError(GraphEdgeResolutionError):
    """``ResultGraphEdge``: action result type not resolvable from generics / schema."""

    def __init__(self, host_qualname: str) -> None:
        msg = (
            "ResultGraphEdge requires a resolvable Result type on the action class "
            f"(ActionSchemaIntentResolver.resolve_result_type); missing or invalid on {host_qualname!r}"
        )
        super().__init__(host_qualname, msg)
