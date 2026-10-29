# packages/maxitor/tools/graph_builder/src/maxitor/graph_builder/writer.py
"""
Build a repository's graphs and keep each one in its file.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``write`` brings every graph file up to date; ``check`` says, without writing,
whether every file already is. Both build each graph the same way, so a file
written on one machine is the file another machine checks against.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

``Graph.build`` → ``bash -c`` in ``Graph.cwd``, a process of its own, with a time
limit → standard output → JSON → ``check_graph`` → ``render`` (sorted keys,
indent 2, one newline) → compared with the file's bytes. A file is written only
when its bytes differ, so an unchanged graph leaves the file untouched.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
from dataclasses import dataclass
from typing import Any

from maxitor.graph_builder.config import Graph
from maxitor.graph_builder.differences import differences
from maxitor.graph_builder.schemas import GraphRefused, check_graph

TIMEOUT_SECONDS = 300.0
TAIL_LINES = 20


class BuildFailed(RuntimeError):
    """
    AI-CORE-BEGIN
    ROLE: A graph's build gave no graph: it failed, took too long, or printed something that is not JSON.
    CONTRACT: ``graph`` is the graph's name, ``reason`` one line, ``output`` the last lines the build printed.
    AI-CORE-END
    """

    def __init__(self, graph: Graph, reason: str, output: str) -> None:
        """Keep what a person needs to fix the build."""
        self.graph = graph.name
        self.command = graph.build
        self.reason = reason
        self.output = "\n".join(output.rstrip().splitlines()[-TAIL_LINES:])
        super().__init__(f"{graph.name}: {reason}")


@dataclass(frozen=True)
class Outcome:
    """
    AI-CORE-BEGIN
    ROLE: What happened to one graph.
    CONTRACT: ``state`` is one of ``written``, ``unchanged`` (write), ``current``, ``stale``, ``missing`` (check), ``failed``, ``refused`` (both); ``details`` are the lines that explain it.
    AI-CORE-END
    """

    graph: Graph
    state: str
    details: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        """Whether the graph's file is, or now is, what its build prints."""
        return self.state in ("written", "unchanged", "current")


def render(document: Any) -> bytes:
    """
    AI-CORE-BEGIN
    ROLE: The bytes a graph file holds.
    CONTRACT: Sorted keys, indent 2, non-ASCII kept, one newline at the end, UTF-8 — the same document always gives the same bytes.
    AI-CORE-END
    """
    return (json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def build(graph: Graph, timeout: float = TIMEOUT_SECONDS) -> dict[str, Any]:
    """
    AI-CORE-BEGIN
    ROLE: Run a graph's build and return the graph it printed.
    CONTRACT: Returns a document that passed ``check_graph``; raises ``BuildFailed`` (failed, timed out, not JSON) or ``GraphRefused`` (JSON but not a graph of its version).
    INVARIANTS: The build runs in a process group of its own, so a time-out stops everything it started.
    AI-CORE-END
    """
    try:
        process = subprocess.Popen(
            ["bash", "-c", graph.build],
            cwd=graph.cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
    except OSError as exc:
        raise BuildFailed(graph, f"could not start in {graph.cwd}: {exc.strerror}", "") from None
    with process:
        try:
            out, err = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            out, err = process.communicate()
            raise BuildFailed(graph, f"took longer than {timeout:g} s", err.decode(errors="replace")) from None
    if process.returncode != 0:
        output = err.decode(errors="replace") + out.decode(errors="replace")
        raise BuildFailed(graph, f"exited with {process.returncode}", output)
    try:
        document = json.loads(out)
    except ValueError as exc:
        raise BuildFailed(graph, f"printed something that is not JSON ({exc})", out.decode(errors="replace")) from None
    check_graph(document)
    return dict(document)


def _built(graph: Graph, timeout: float) -> tuple[bytes, dict[str, Any]] | Outcome:
    """The graph's bytes and document, or the outcome that says why there are none."""
    try:
        document = build(graph, timeout)
    except BuildFailed as failed:
        return Outcome(graph, "failed", (failed.reason, f"$ {failed.command}", *failed.output.splitlines()))
    except GraphRefused as refused:
        return Outcome(graph, "refused", (str(refused),))
    return render(document), document


def write(graphs: list[Graph], timeout: float = TIMEOUT_SECONDS) -> list[Outcome]:
    """
    AI-CORE-BEGIN
    ROLE: Bring every graph file up to date.
    CONTRACT: One outcome per graph, in order; a file is written only when its bytes differ, and never from a failed or refused build.
    AI-CORE-END
    """
    outcomes: list[Outcome] = []
    for graph in graphs:
        built = _built(graph, timeout)
        if isinstance(built, Outcome):
            outcomes.append(built)
            continue
        data, _ = built
        if graph.file.is_file() and graph.file.read_bytes() == data:
            outcomes.append(Outcome(graph, "unchanged"))
            continue
        graph.file.parent.mkdir(parents=True, exist_ok=True)
        graph.file.write_bytes(data)
        outcomes.append(Outcome(graph, "written"))
    return outcomes


def check(graphs: list[Graph], timeout: float = TIMEOUT_SECONDS) -> list[Outcome]:
    """
    AI-CORE-BEGIN
    ROLE: Say whether every graph file is what its build prints, writing nothing.
    CONTRACT: One outcome per graph, in order: ``current``, ``stale`` with the differences by id (or that only the formatting differs), ``missing``, ``failed`` or ``refused``.
    AI-CORE-END
    """
    outcomes: list[Outcome] = []
    for graph in graphs:
        built = _built(graph, timeout)
        if isinstance(built, Outcome):
            outcomes.append(built)
            continue
        data, document = built
        if not graph.file.is_file():
            outcomes.append(Outcome(graph, "missing"))
            continue
        saved = graph.file.read_bytes()
        if saved == data:
            outcomes.append(Outcome(graph, "current"))
            continue
        try:
            lines = differences(json.loads(saved), document) or ["only the formatting differs"]
        except ValueError:
            lines = ["the saved file is not JSON"]
        outcomes.append(Outcome(graph, "stale", tuple(lines)))
    return outcomes
