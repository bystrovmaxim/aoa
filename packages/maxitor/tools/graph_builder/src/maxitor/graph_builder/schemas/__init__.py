# packages/maxitor/tools/graph_builder/src/maxitor/graph_builder/schemas/__init__.py
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

The schemas belong to the Open Gnomon Protocol, ``packages/open-gnomon-protocol/graph/<version>.json``
in this repository; the files beside this module, ``<version>.json``, are copies of them,
kept byte for byte by ``tests/scripts/test_schema_copies.py``. A published version never
changes; a new shape of the graph is a new file and a new entry in ``SCHEMA_VERSIONS``.
``1.0`` is the first shape; ``1.1`` gave every edge an ``id``.

Two validators share the work. ``jsonschema-rs`` decides whether a document is a
graph — a union of 21 node shapes and 17 edge shapes makes a pure-Python check of
a large graph take tens of seconds. When it refuses, ``jsonschema`` explains why
on the one node or edge it stopped at, narrowed to the shape that node or edge
was meant to have.
"""

from __future__ import annotations

import json
from functools import cache
from importlib.resources import files
from typing import Any

import jsonschema_rs
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError, best_match

SCHEMA_VERSIONS: tuple[str, ...] = ("1.0", "1.1")
SHOWN_CHARACTERS = 200


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
    text = files(__package__).joinpath(f"{version}.json").read_text(encoding="utf-8")
    schema: dict[str, Any] = json.loads(text)
    return schema


@cache
def _deciding(version: str) -> jsonschema_rs.Validator:
    """The fast validator of one version, built once."""
    return jsonschema_rs.validator_for(graph_schema(version))


@cache
def _explaining(version: str) -> Draft202012Validator:
    """The validator that explains a refusal, built once."""
    return Draft202012Validator(graph_schema(version))


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
    stop = next(iter(_deciding(version).iter_errors(document)), None)
    if stop is None:
        return
    raise _explained(version, document, list(stop.instance_path), stop.message)


def _explained(version: str, document: dict[str, Any], stop: list[str | int], message: str) -> GraphRefused:
    """
    Why ``document`` is refused, said at the place the fast validator stopped.

    A node or an edge is checked alone — a document holding only that element — so the explanation costs
    one element, not the graph; its path is then put back at the element's real index.
    """
    element = len(stop) >= 2 and stop[0] in ("nodes", "edges") and isinstance(stop[1], int)
    if element:
        array, index = str(stop[0]), int(stop[1])
        alone = {**document, "nodes": [], "edges": [], array: [document[array][index]]}
        error = best_match(_explaining(version).iter_errors(alone))
    else:
        error = best_match(_explaining(version).iter_errors(document))
    if error is None:
        return GraphRefused(version, "/".join(map(str, stop)), message[:SHOWN_CHARACTERS])
    error = _narrowed(error)
    path = list(error.absolute_path)
    if element:
        path[1] = index
    if error.validator in ("oneOf", "anyOf"):
        # A union's own message repeats the whole value; the path already says which one it is.
        reason = "matches none of the shapes allowed here"
    elif error.validator == "uniqueItems":
        reason = "holds the same element twice"
    else:
        reason = error.message[:SHOWN_CHARACTERS]
    return GraphRefused(version, "/".join(map(str, path)), reason)
