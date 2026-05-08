# packages/aoa-action-machine/src/aoa/action_machine/exceptions/params_graph_edge_resolution_error.py
"""ParamsGraphEdgeResolutionError."""


from __future__ import annotations

from aoa.action_machine.exceptions.graph_edge_resolution_error import GraphEdgeResolutionError


class ParamsGraphEdgeResolutionError(GraphEdgeResolutionError):
    """``ParamsGraphEdge``: action params type not resolvable from generics / schema."""

    def __init__(self, host_qualname: str) -> None:
        msg = (
            "ParamsGraphEdge requires a resolvable Params type on the action class "
            f"(ActionSchemaIntentResolver.resolve_params_type); missing or invalid on {host_qualname!r}"
        )
        super().__init__(host_qualname, msg)
