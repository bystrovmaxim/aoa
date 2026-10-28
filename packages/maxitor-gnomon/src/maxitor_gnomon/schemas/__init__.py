# packages/maxitor-gnomon/src/maxitor_gnomon/schemas/__init__.py
"""
The graph schema, by version.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A graph document says which schema it follows in ``schema_version``. This module
returns that schema and checks a document against it, so any reader can tell a
graph from something else without knowing who produced it.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

The schemas are files beside this module, ``graph/<version>.json``. A published
version never changes; a new shape of the graph is a new file and a new entry in
``SCHEMA_VERSIONS``. ``1.0`` is the first shape; ``1.1`` gave every edge an ``id``.
"""

from __future__ import annotations

import json
from functools import cache
from importlib.resources import files
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError, best_match

SCHEMA_VERSIONS: tuple[str, ...] = ("1.0", "1.1")


class GraphRefused(ValueError):
    """
    AI-CORE-BEGIN
    ROLE: A document refused as a graph: which version it claimed, where it is wrong, and why.
    CONTRACT: ``version`` is the claimed ``schema_version`` (``None`` when absent); ``path`` is the JSON path of the first error, ``""`` for the document itself; ``reason`` says what is wrong.
    AI-CORE-END
    """

    def __init__(self, version: str | None, path: str, reason: str) -> None:
        """Keep the three parts and say them in one line."""
        self.version = version
        self.path = path
        self.reason = reason
        where = f" at {path}" if path else ""
        super().__init__(f"graph {version or '(no version)'}{where}: {reason}")


@cache
def graph_schema(version: str) -> dict[str, Any]:
    """
    AI-CORE-BEGIN
    ROLE: The JSON Schema of one graph version.
    CONTRACT: Returns the schema as a dict, read once and cached — callers must not change it; an unknown version raises ``GraphRefused`` naming it.
    AI-CORE-END
    """
    if version not in SCHEMA_VERSIONS:
        known = ", ".join(SCHEMA_VERSIONS)
        raise GraphRefused(version, "", f"unknown schema version {version!r}; known: {known}")
    text = files(__package__).joinpath("graph", f"{version}.json").read_text(encoding="utf-8")
    schema: dict[str, Any] = json.loads(text)
    return schema


def _narrowed(error: ValidationError) -> ValidationError:
    """
    The error inside the one branch of a ``oneOf`` / ``anyOf`` the value was meant for.

    A node or an edge is a union told apart by a ``const`` (its ``type``); the branches whose ``const`` or
    ``enum`` does not match were never meant, so when exactly one branch is left, its own error is the answer.
    """
    branches: dict[object, list[ValidationError]] = {}
    for sub in error.context or ():
        branches.setdefault(sub.relative_schema_path[0], []).append(sub)
    meant = [errors for errors in branches.values() if not any(e.validator in ("const", "enum") for e in errors)]
    if len(meant) != 1:
        return error
    inner = best_match(meant[0])
    return error if inner is None else _narrowed(inner)


def check_graph(document: object) -> None:
    """
    AI-CORE-BEGIN
    ROLE: Decide whether a document is a graph of the version it claims.
    CONTRACT: Returns ``None`` for a valid graph; otherwise raises ``GraphRefused`` — no version, an unknown version, or the first schema error with its JSON path.
    AI-CORE-END
    """
    if not isinstance(document, dict):
        raise GraphRefused(None, "", "a graph document is a JSON object")
    version = document.get("schema_version")
    if version is None:
        raise GraphRefused(None, "", "the document has no schema_version")
    if not isinstance(version, str):
        raise GraphRefused(None, "schema_version", f"schema_version must be a string, got {version!r}")
    error = best_match(Draft202012Validator(graph_schema(version)).iter_errors(document))
    if error is not None:
        error = _narrowed(error)
        path = "/".join(str(part) for part in error.absolute_path)
        # A union's own message repeats the whole value; the path already says which one it is.
        reason = "matches none of the shapes allowed here" if error.validator in ("oneOf", "anyOf") else error.message
        raise GraphRefused(version, path, reason)
