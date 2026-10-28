# packages/maxitor-gnomon/src/maxitor_gnomon/cli.py
"""
The ``gnomon`` command: ``write``, ``check``, ``validate`` and ``skill``.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A developer runs ``gnomon write`` and commits the graph files with the change;
CI runs ``gnomon check`` and fails when a file is stale. ``validate`` tells
whether one document is a graph, ``skill`` prints the setup skill for agents.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

``read_config`` → ``writer.write`` / ``writer.check`` → one line per graph, the
lines that explain a failure, and the command that fixes it. Exit codes: 0 —
every graph is fine; 1 — a graph is not; 2 — the config was refused.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Callable, Sequence
from importlib.resources import files
from pathlib import Path

from maxitor_gnomon import __version__
from maxitor_gnomon.config import ConfigRefused, Graph, read_config
from maxitor_gnomon.schemas import GraphRefused, check_graph
from maxitor_gnomon.writer import Outcome, check, write

DEFAULT_CONFIG = "gnomon.toml"


def _shown_path(path: Path) -> str:
    """A path as a person in the current folder would type it."""
    relative = os.path.relpath(path)
    return relative if not relative.startswith("..") else str(path)


def _line(outcome: Outcome) -> str:
    """The one line that says what happened to a graph."""
    name = outcome.graph.name
    if outcome.state in ("written", "unchanged"):
        return f"ok {name} ({outcome.state})"
    if outcome.state == "current":
        return f"ok {name}"
    if outcome.state in ("stale", "missing"):
        return f"{outcome.state} {name}: {_shown_path(outcome.graph.file)}"
    return f"{outcome.state} {name}"


def _report(outcomes: list[Outcome], config: str) -> int:
    """Print every outcome and, when one is not fine, the command that fixes it."""
    for outcome in outcomes:
        print(_line(outcome))
        for detail in outcome.details:
            print(f"  {detail}")
    broken = [o.graph.name for o in outcomes if o.state in ("failed", "refused")]
    if broken:
        print(f"fix the build of {', '.join(broken)}, then run: gnomon write --config {config}")
    elif not all(o.ok for o in outcomes):
        print(f"run: gnomon write --config {config}, and commit the graph files")
    return 0 if all(o.ok for o in outcomes) else 1


def _run(config: str, action: Callable[[list[Graph]], list[Outcome]]) -> int:
    """Read the config and report what ``action`` did with its graphs."""
    try:
        graphs = read_config(config)
    except ConfigRefused as refused:
        print(f"config refused: {config}: {refused}", file=sys.stderr)
        return 2
    return _report(action(graphs), config)


def _validate(source: str) -> int:
    """Say whether one document — a file, or ``-`` for standard input — is a graph."""
    try:
        text = sys.stdin.read() if source == "-" else Path(source).read_text(encoding="utf-8")
    except OSError as exc:
        print(f"refused: cannot read {source}: {exc.strerror}")
        return 1
    try:
        document = json.loads(text)
        check_graph(document)
    except ValueError as exc:
        reason = str(exc) if isinstance(exc, GraphRefused) else f"not JSON ({exc})"
        print(f"refused: {reason}")
        return 1
    print(f"ok {document['schema_version']}: {len(document['nodes'])} nodes, {len(document['edges'])} edges")
    return 0


def _skill() -> int:
    """Print the setup skill for coding agents, to be saved as ``<skills folder>/gnomon-setup/SKILL.md``."""
    sys.stdout.write(files("maxitor_gnomon").joinpath("skills", "gnomon-setup", "SKILL.md").read_text(encoding="utf-8"))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """
    AI-CORE-BEGIN
    ROLE: The ``gnomon`` console script.
    CONTRACT: Returns the exit code: 0 — fine; 1 — a graph is not (stale, missing, failed, refused, not a graph); 2 — the config was refused.
    AI-CORE-END
    """
    parser = argparse.ArgumentParser(prog="gnomon", description="Keep each graph of a repository in its file.")
    parser.add_argument("--version", action="version", version=f"gnomon {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)
    for name, about in (
        ("write", "build every graph and write the files that changed"),
        ("check", "build every graph and fail if a file is not what its build prints; writes nothing"),
    ):
        command = commands.add_parser(name, help=about, description=about)
        command.add_argument("--config", default=DEFAULT_CONFIG, help=f"the config (default: {DEFAULT_CONFIG})")
    validate = commands.add_parser("validate", help="say whether one document is a graph")
    validate.add_argument("source", help="a graph file, or - for standard input")
    commands.add_parser("skill", help="print the gnomon-setup skill for coding agents")
    args = parser.parse_args(argv)
    if args.command == "write":
        return _run(args.config, write)
    if args.command == "check":
        return _run(args.config, check)
    if args.command == "validate":
        return _validate(args.source)
    return _skill()


if __name__ == "__main__":
    raise SystemExit(main())
