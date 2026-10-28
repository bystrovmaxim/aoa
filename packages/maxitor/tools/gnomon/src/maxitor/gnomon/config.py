# packages/maxitor/tools/gnomon/src/maxitor/gnomon/config.py
"""
Read ``gnomon.toml``: the graphs of one repository.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A repository lists its graphs in one file. Each ``[[graph]]`` names a graph, the
folder its build runs in, the shell command that prints it, and the file it is
saved in. This module reads that file into ``Graph`` values, or refuses it naming
the graph and the field that are wrong.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

TOML → the config's own version (``gnomon = "1.0"``) → its JSON Schema
(``config_schema.json`` beside this module, the one config version there is) → the rules a schema cannot say: names and
files unique → ``Graph`` values with paths resolved against the config's folder.
"""

from __future__ import annotations

import json
import tomllib
from dataclasses import dataclass
from functools import cache
from importlib.resources import files
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError, best_match

CONFIG_VERSIONS: tuple[str, ...] = ("1.0",)


@dataclass(frozen=True)
class Graph:
    """
    AI-CORE-BEGIN
    ROLE: One graph of a repository: what it is called, where and how it is built, where it is saved.
    INVARIANTS: ``cwd`` and ``file`` are absolute, resolved against the config's folder; ``name`` and ``file`` are unique within one config.
    AI-CORE-END
    """

    name: str
    cwd: Path
    build: str
    file: Path


class ConfigRefused(ValueError):
    """
    AI-CORE-BEGIN
    ROLE: A config refused: which graph, which field, and why.
    CONTRACT: ``graph`` is the graph's name (``#n`` when it has none, ``None`` for the config itself); ``field`` is the field at fault, ``""`` for the whole file.
    AI-CORE-END
    """

    def __init__(self, graph: str | None, field: str, reason: str) -> None:
        """Keep the three parts and say them in one line."""
        self.graph = graph
        self.field = field
        self.reason = reason
        where = [f"graph {graph!r}"] if graph is not None else []
        where += [field] if field else []
        super().__init__(f"{', '.join(where)}: {reason}" if where else reason)


@cache
def _config_schema() -> dict[str, Any]:
    """The JSON Schema of the config, version ``1.0``, read once."""
    text = files("maxitor.gnomon").joinpath("config_schema.json").read_text(encoding="utf-8")
    schema: dict[str, Any] = json.loads(text)
    return schema


def _graph_label(document: dict[str, Any], index: int) -> str:
    """How a refusal names the graph at ``index``: its name, or its place when it has none."""
    entry = document["graph"][index]
    name = entry.get("name") if isinstance(entry, dict) else None
    return name if isinstance(name, str) and name else f"#{index + 1}"


def _refusal(document: dict[str, Any], error: ValidationError) -> ConfigRefused:
    """Turn the first schema error into a refusal that names the graph and the field."""
    path = list(error.absolute_path)
    in_graph = len(path) >= 2 and path[0] == "graph" and isinstance(path[1], int)
    graph = _graph_label(document, int(path[1])) if in_graph else None
    inner = path[2:] if graph is not None else path
    instance, schema = error.instance, error.schema
    if error.validator == "required" and isinstance(instance, dict) and isinstance(error.validator_value, list):
        missing = [name for name in error.validator_value if name not in instance]
        return ConfigRefused(graph, ".".join(map(str, [*inner, missing[0]])), "required")
    if error.validator == "additionalProperties" and isinstance(instance, dict) and isinstance(schema, dict):
        unknown = sorted(set(instance) - set(schema.get("properties", {})))
        return ConfigRefused(graph, ".".join(map(str, [*inner, unknown[0]])), "not a field of the config")
    return ConfigRefused(graph, ".".join(map(str, inner)), error.message)


def read_config(path: str | Path) -> list[Graph]:
    """
    AI-CORE-BEGIN
    ROLE: Read a repository's ``gnomon.toml`` into its graphs.
    CONTRACT: Returns the graphs in file order, paths absolute; raises ``ConfigRefused`` naming the graph and the field — a missing file, not TOML, no or unknown ``gnomon`` version, a missing or unknown field, a repeated name, two graphs with one file.
    AI-CORE-END
    """
    config = Path(path)
    try:
        document = tomllib.loads(config.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ConfigRefused(None, "", f"no config at {config}") from None
    except tomllib.TOMLDecodeError as exc:
        raise ConfigRefused(None, "", f"not TOML: {exc}") from None
    version = document.get("gnomon")
    if version is None:
        raise ConfigRefused(None, "gnomon", 'required: the config\'s format version, gnomon = "1.0"')
    if version not in CONFIG_VERSIONS:
        known = ", ".join(CONFIG_VERSIONS)
        raise ConfigRefused(None, "gnomon", f"unknown config version {version!r}; known: {known}")
    error = best_match(Draft202012Validator(_config_schema()).iter_errors(document))
    if error is not None:
        raise _refusal(document, error)
    base = config.resolve().parent
    graphs: list[Graph] = []
    for entry in document["graph"]:
        graph = Graph(
            name=entry["name"],
            cwd=(base / entry.get("cwd", ".")).resolve(),
            build=entry["build"],
            file=(base / entry["file"]).resolve(),
        )
        for earlier in graphs:
            if earlier.name == graph.name:
                raise ConfigRefused(graph.name, "name", "another graph has this name")
            if earlier.file == graph.file:
                raise ConfigRefused(graph.name, "file", f"graph {earlier.name!r} is saved in this file too")
        graphs.append(graph)
    return graphs
