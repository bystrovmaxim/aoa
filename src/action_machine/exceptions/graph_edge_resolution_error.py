# src/action_machine/exceptions/graph_edge_resolution_error.py
"""GraphEdgeResolutionError."""


from __future__ import annotations


class GraphEdgeResolutionError(ValueError):
    """
    Base for interchange edge construction failures due to missing resolver output.

    :attr:`host_qualname` is the dotted name of the host class passed to the edge constructor.
    """

    host_qualname: str

    def __init__(self, host_qualname: str, message: str) -> None:
        self.host_qualname = host_qualname
        super().__init__(message)
