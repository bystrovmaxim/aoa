# tests/maxitor/test_erd_table_rows_and_palette.py
"""
Tests for what an ERD table row and a domain colour say after spec 027.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

An FK row's type is the target table's name alone — the ``FK`` badge and the line
already say the rest. No domain is grey: grey is the colour of entity kinds in the
ERD, so a kind disk is never read as a domain.
"""

from __future__ import annotations

import gzip
import json
from pathlib import Path

from maxitor.viewer.model.diagrams.actions.list_domains_action import _LIST_DOMAINS_DISTINCT_COLORS
from maxitor.viewer.model.diagrams.actions.list_entities_action import ListEntitiesAction
from maxitor.viewer.model.diagrams.resources.duckdb_graph_resource import DuckDBGraphResource

_REFERENCE_GRAPH = Path(__file__).resolve().parents[4] / "specs/025-graph-index-memory/data/ref-graph-2026-10-26.json.gz"


def test_an_fk_row_names_its_target_table_alone() -> None:
    """``UserEventCoreEntity``'s ``player`` row reads ``PlayerCoreEntity``, not ``FK -> PlayerCoreEntity``."""
    data = json.loads(gzip.decompress(_REFERENCE_GRAPH.read_bytes()))
    data = data.get("coordinator_json", data)
    graph = json.loads(data) if isinstance(data, str) else data
    events = next(n["id"] for n in graph["nodes"] if n["type"] == "Domain" and n["id"].endswith("EventsDomain"))

    payload = ListEntitiesAction._slice_payload(DuckDBGraphResource.build_from_json(graph), events, include_neighbors=True)
    core = next(e for e in payload["entities"] if e["id"].endswith("UserEventCoreEntity"))
    fk_rows = [f for f in core["fields"] if f["foreign_key"]]

    assert {"name": "player", "type": "PlayerCoreEntity"}.items() <= next(f for f in fk_rows if f["name"] == "player").items()
    assert not [f for f in fk_rows if f["type"].startswith("FK -> ")]


def _is_grey(hex_color: str) -> bool:
    """A colour with a saturation under 0.35 reads as grey (slate ``#64748b`` is 0.28, ``#94a3b8`` 0.20)."""
    r, g, b = (int(hex_color[i : i + 2], 16) for i in (1, 3, 5))
    return (max(r, g, b) - min(r, g, b)) / max(r, g, b, 1) < 0.35


def test_no_domain_colour_is_grey() -> None:
    """Grey is the kinds' colour: the domain palette holds none, and slate's place is orange."""
    assert [c for c in _LIST_DOMAINS_DISTINCT_COLORS if _is_grey(c)] == []
    assert _LIST_DOMAINS_DISTINCT_COLORS[7] == "#f97316"
