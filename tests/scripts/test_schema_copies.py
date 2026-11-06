# tests/scripts/test_schema_copies.py
"""AOA's copy of the graph schema is version 1.8 of the Open Gnomon Protocol as published, unchanged."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
COPY = REPO_ROOT / "packages" / "aoa-action-machine" / "src" / "aoa" / "action_machine" / "graph" / "graph_json_schema.json"

# The protocol lives in bystrovmaxim/gnomon. Version 1.8 was published there (gnomon#51) with this ``$id`` and this
# SHA-256 of the schema without its ``$id``, as ``json.dumps(..., sort_keys=True)``. A published version never changes,
# so a copy that drifts from it is no longer version 1.8.
PUBLISHED_ID = "https://raw.githubusercontent.com/bystrovmaxim/gnomon/main/packages/open-gnomon-protocol/graph/1.8.json"
PUBLISHED_SHA256 = "816d238f7b4c3c327a3b758693c329993b6e7f015e562590dca60d15ac0c1ecb"


def test_aoas_copy_is_the_published_version() -> None:
    """The copy names version 1.8's ``$id`` and has the content it was published with."""
    schema = json.loads(COPY.read_text(encoding="utf-8"))
    assert schema.pop("$id") == PUBLISHED_ID
    assert hashlib.sha256(json.dumps(schema, sort_keys=True).encode()).hexdigest() == PUBLISHED_SHA256, (
        "graph_json_schema.json differs from version 1.8 as published; copy gnomon's "
        "packages/open-gnomon-protocol/graph/1.8.json over it"
    )
