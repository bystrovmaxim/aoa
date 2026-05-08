# packages/aoa-action-machine/src/aoa/action_machine/exceptions/domain_graph_edge_resolution_error.py
"""DomainGraphEdgeResolutionError."""


from __future__ import annotations

from aoa.action_machine.exceptions.graph_edge_resolution_error import GraphEdgeResolutionError


class DomainGraphEdgeResolutionError(GraphEdgeResolutionError):
    """``DomainGraphEdge``: ``@meta(domain=...)`` missing or does not resolve to a domain type."""

    def __init__(self, host_qualname: str) -> None:
        msg = (
            "DomainGraphEdge requires @meta(..., domain=<BaseDomain subtype>) on host; "
            f"missing or invalid on {host_qualname!r}"
        )
        super().__init__(host_qualname, msg)
