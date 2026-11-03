# packages/maxitor/tools/repo-graph-port/maxitor/repo_graph_port/version_source.py
"""
VersionSource — read one key of a version file, and say why it cannot be read.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A history may name the file that holds its version and the key inside it. The file
is TOML or JSON, by its extension, so the port reads any level's number without
knowing a language. A number is read, never computed: a computed or inherited
version is reported, not resolved.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

Pure, no I/O: the mirror reads the file, this reads the file's bytes.

::

    file name + bytes + dotted key ──► read_number ──► NumberRead(number | reason)
"""

from __future__ import annotations

import json
import tomllib
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any

MISSING = "missing"
NOT_A_STRING = "not a string"
BROKEN = "broken"
FORMAT = "format"
DRIVER = "driver"


@dataclass(frozen=True)
class NumberRead:
    """A number, or the reason there is none."""

    number: str | None = None
    reason: str | None = None


def read_number(file_name: str, content: bytes, key: str) -> NumberRead:
    """
    AI-CORE-BEGIN
    ROLE: Read the version a file holds under a dotted key.
    CONTRACT: ``.toml`` and ``.json`` are read; any other extension gives the reason ``format``. Bytes that do not parse give ``broken``; a missing key gives ``missing``, or ``driver`` when the document names a driver instead; a value that is not a non-empty string gives ``not a string``. Never raises for any bytes.
    AI-CORE-END
    """
    suffix = PurePosixPath(file_name).suffix
    if suffix not in (".toml", ".json"):
        return NumberRead(reason=FORMAT)
    try:
        document = tomllib.loads(content.decode("utf-8")) if suffix == ".toml" else json.loads(content)
    except ValueError:
        return NumberRead(reason=BROKEN)
    value: Any = document
    for part in key.split("."):
        if not isinstance(value, dict) or part not in value:
            return NumberRead(reason=DRIVER if isinstance(document, dict) and "driver" in document else MISSING)
        value = value[part]
    return NumberRead(number=value) if isinstance(value, str) and value else NumberRead(reason=NOT_A_STRING)
