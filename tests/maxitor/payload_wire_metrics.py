# tests/maxitor/payload_wire_metrics.py
"""
Full-graph JSON wire-size helpers (PR-3 methodology).

Uncompressed: canonical ``json.dumps(..., separators=(',', ':')).encode('utf-8')`` length.
Gzip: ``gzip.compress(raw, compresslevel=6)`` length (typical middle ground vs nginx defaults).

``simulate_pre_pr1_fat_payload`` overlays keys removed in PR-1/PR-2 so before/after is
comparable on the *same* graph without a historical snapshot.
"""

from __future__ import annotations

import copy
import gzip
import json
from typing import Any

_SAMPLE_PAYLOAD_BLOB: dict[str, Any] = {
    "description": "x" * 120,
    "fields": [{"name": f"f{k}", "t": "str"} for k in range(8)],
}


def interchange_json_bytes(payload: dict[str, Any]) -> bytes:
    """Canonical UTF-8 JSON for interchange wire-size (no extra whitespace)."""
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def uncompressed_and_gzip_len(payload: dict[str, Any], gzip_level: int = 6) -> tuple[int, int]:
    """Return ``(len(raw_json_utf8), len(gzip(raw)))``."""
    raw = interchange_json_bytes(payload)
    return len(raw), len(gzip.compress(raw, compresslevel=gzip_level))


def simulate_pre_pr1_fat_payload(slim: dict[str, Any]) -> dict[str, Any]:
    """Return a deep copy with legacy ``nodes[].data`` / ``edges[].data`` fat keys restored."""
    fat: dict[str, Any] = copy.deepcopy(slim)
    blob = copy.deepcopy(_SAMPLE_PAYLOAD_BLOB)
    for n in fat.get("nodes") or []:
        if not isinstance(n, dict):
            continue
        d = n.setdefault("data", {})
        if not isinstance(d, dict):
            continue
        nid = str(n.get("id", ""))
        fill = d.get("fill", "#000")
        nt = d.get("node_type", "Action")
        short = d.get("label", "?")
        d["graph_node_subtitle"] = f"{nt}\n{short}"
        d["graph_key"] = nid
        d["qualified"] = nid
        d["typeFill"] = fill
        d["isDagCycleViolationIncident"] = False
        d["payload"] = copy.deepcopy(blob)
    for e in fat.get("edges") or []:
        if not isinstance(e, dict):
            continue
        d = e.setdefault("data", {})
        if not isinstance(d, dict):
            continue
        rel = d.get("label", "")
        d["isDag"] = False
        d["isForbiddenDagCycle"] = False
        d["relationshipName"] = str(rel)
        d["sourceAttachment"] = "none"
        d["targetAttachment"] = "arrow"
        d["lineStyle"] = "solid"
        d["payload"] = copy.deepcopy(blob)
    return fat


def synthetic_sql_rows(num_domains: int, actions_per_domain: int) -> list[dict[str, Any]]:
    """Build minimal ``execute_fetch_dicts``-shaped rows for :func:`_build_payload_from_duckdb`."""
    rows: list[dict[str, Any]] = []
    edge_idx = 0
    empty = {
        "idx": None,
        "source_id": None,
        "target_id": None,
        "relationship": None,
        "is_dag": None,
        "payload": None,
    }
    for i in range(num_domains):
        did = f"q.domain{i}"
        rows.append(
            {
                "result_type": "nodes",
                "pk": did,
                "label": did,
                "type": "domain",
                **empty,
            },
        )
        rows.append(
            {
                "result_type": "domain",
                "pk": did,
                "label": None,
                "type": None,
                **empty,
            },
        )
        for j in range(actions_per_domain):
            aid = f"{did}.Action{j}"
            rows.append(
                {
                    "result_type": "nodes",
                    "pk": aid,
                    "label": aid,
                    "type": "action",
                    **empty,
                },
            )
            rows.append(
                {
                    "result_type": "edges",
                    "pk": str(edge_idx),
                    "label": None,
                    "type": "field",
                    "idx": edge_idx,
                    "source_id": did,
                    "target_id": aid,
                    "relationship": "composition",
                    "is_dag": None,
                    "payload": None,
                },
            )
            edge_idx += 1
    return rows
