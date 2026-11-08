# tests/scripts/test_schema_copies.py
"""AOA's copy of the graph schema is version 2.0 of the Open Gnomon Protocol as published, unchanged."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
COPY = REPO_ROOT / "packages" / "aoa-action-machine" / "src" / "aoa" / "action_machine" / "graph" / "graph_json_schema.json"

# The protocol lives in bystrovmaxim/gnomon. Version 2.0 was published there (gnomon#66, commit 5d9dac89) with this
# ``$id`` and this SHA-256 of the schema without its ``$id``, as ``json.dumps(..., sort_keys=True)``. A published
# version never changes, so a copy that drifts from it is no longer version 2.0.
PUBLISHED_ID = "https://raw.githubusercontent.com/bystrovmaxim/gnomon/main/packages/open-gnomon-protocol/graph/2.0.json"
PUBLISHED_SHA256 = "19d1bdd631514cc8c2124a200a8286d5e93510bbdbe575d5d0cc84babac7a50d"


def test_aoas_copy_is_the_published_version() -> None:
    """The copy names version 2.0's ``$id`` and has the content it was published with."""
    schema = json.loads(COPY.read_text(encoding="utf-8"))
    assert schema.pop("$id") == PUBLISHED_ID
    assert hashlib.sha256(json.dumps(schema, sort_keys=True).encode()).hexdigest() == PUBLISHED_SHA256, (
        "graph_json_schema.json differs from version 2.0 as published; copy gnomon's "
        "packages/open-gnomon-protocol/graph/2.0.json over it"
    )
