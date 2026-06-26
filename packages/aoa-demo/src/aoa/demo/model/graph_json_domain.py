# packages/aoa-demo/src/aoa/demo/model/graph_json_domain.py
"""Domain marker for example interchange graph JSON export."""

from __future__ import annotations

from aoa.action_machine.domain import BaseDomain


class ExampleModelGraphJsonDomain(BaseDomain):
    """Interchange graph JSON built from the registered example model."""

    name = "example_model_graph"
    description = "Demo NodeGraphCoordinator JSON for tooling and Maxitor."
