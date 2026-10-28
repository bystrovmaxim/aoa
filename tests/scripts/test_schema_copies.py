# tests/scripts/test_schema_copies.py
"""The Open Gnomon Protocol is a folder with no code; every Python copy of its schemas is byte for byte its source."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = REPO_ROOT / "packages" / "open-gnomon-protocol"
RAW = "https://raw.githubusercontent.com/bystrovmaxim/aoa/main/packages/open-gnomon-protocol/"

# Each copy a Python package keeps beside its code, and the protocol file it copies.
COPIES = {
    "packages/aoa-action-machine/src/aoa/action_machine/graph/graph_json_schema.json": "graph/1.1.json",
    "packages/maxitor/src/maxitor/gnomon/schemas/1.0.json": "graph/1.0.json",
    "packages/maxitor/src/maxitor/gnomon/schemas/1.1.json": "graph/1.1.json",
}

# SHA-256 of each published schema without its ``$id``, as ``json.dumps(..., sort_keys=True)``.
# A published version never changes: a new shape of the graph is a new version, not an edit.
PUBLISHED = {
    "1.0": "77f1a7960a09dcb63b31d75e9d08467dd34c28e563281f959beb087c615b9bb4",
    "1.1": "4d5e7bbe4efadbbba63a03a598a8784c240db5d81322cd0fd794d726c2b5adde",
}


@pytest.mark.parametrize(("copy", "source"), sorted(COPIES.items()))
def test_a_copy_is_its_source_byte_for_byte(copy: str, source: str) -> None:
    """A copy that drifts from the protocol's file is named together with that file."""
    assert (REPO_ROOT / copy).read_bytes() == (PROTOCOL / source).read_bytes(), (
        f"{copy} differs from packages/open-gnomon-protocol/{source}; copy the protocol's file over it"
    )


def test_the_protocol_holds_no_code() -> None:
    """The protocol is its specification, its changelog and its schemas — nothing any language would have to run."""
    held = sorted(str(p.relative_to(PROTOCOL)) for p in PROTOCOL.rglob("*") if p.is_file())
    assert held == ["CHANGELOG.md", "README.md", "graph/1.0.json", "graph/1.1.json"]


@pytest.mark.parametrize("version", sorted(PUBLISHED))
def test_a_published_version_never_changes(version: str) -> None:
    """Each schema's ``$id`` is the raw address of its own file, and its content has the hash it was published with."""
    schema = json.loads((PROTOCOL / "graph" / f"{version}.json").read_text(encoding="utf-8"))
    assert schema.pop("$id") == f"{RAW}graph/{version}.json"
    assert hashlib.sha256(json.dumps(schema, sort_keys=True).encode()).hexdigest() == PUBLISHED[version]
