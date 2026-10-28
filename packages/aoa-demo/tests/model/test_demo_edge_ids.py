# tests/model/test_demo_edge_ids.py
"""
Demo interchange graph — every edge has an id, and the edges that repeat between two nodes are told apart.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The demo graph has ``entity_relation`` and ``lifecycle_transition`` edges that repeat
between the same two nodes. Their ids must still differ, and every id the export writes
must be the id :func:`aoa.action_machine.graph.edge_identity.edge_id` computes from the row.
"""

from __future__ import annotations

import json
from collections import Counter
from typing import Any

from aoa.action_machine.graph.edge_identity import edge_id
from aoa.demo.model.interchange_demo_coordinator import (
    build_registered_interchange_coordinator,
    import_sample_registration_modules,
)


def _export() -> dict[str, Any]:
    import_sample_registration_modules()
    return json.loads(build_registered_interchange_coordinator().to_json())


def test_every_demo_edge_has_its_own_id() -> None:
    """No two edges share an id, and each repeating source-type-target pair gets distinct ids."""
    edges = _export()["edges"]
    ids = [edge["id"] for edge in edges]
    by_pair: dict[tuple[str, str, str], set[str]] = {}
    for edge in edges:
        by_pair.setdefault((edge["source_id"], edge["type"], edge["target_id"]), set()).add(edge["id"])
    repeating = Counter((e["source_id"], e["type"], e["target_id"]) for e in edges)

    assert len(set(ids)) == len(ids)
    assert {pair[1] for pair, count in repeating.items() if count > 1} == {"entity_relation", "lifecycle_transition"}
    assert all(len(by_pair[pair]) == count for pair, count in repeating.items())


def test_every_demo_edge_id_is_computed_from_its_row() -> None:
    """A reader that drops ``id`` computes exactly the id the export wrote."""
    for edge in _export()["edges"]:
        assert edge_id({key: value for key, value in edge.items() if key != "id"}) == edge["id"]
