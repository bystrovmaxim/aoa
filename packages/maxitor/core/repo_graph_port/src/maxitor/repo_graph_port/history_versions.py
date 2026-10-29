# packages/maxitor/core/repo_graph_port/src/maxitor/repo_graph_port/history_versions.py
"""
The rules of a history: where a tag lands, and what a version's file says.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Two decisions every reader of a history must make the same way. A tag is placed
on the newest version whose commit is an ancestor-or-self of the tag's commit on
the branch's first-parent chain — so a tag on a later commit that did not change
the graph lands on the version before it, and a tag off that chain is not placed.
A version's file is a graph, counted, or it is refused with the protocol's reason.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

Pure functions, no I/O: the mirror reads, these decide.

::

    first-parent chain + version shas + tags ──► place_tags ──► {version sha: tag names}
    a version's file bytes                   ──► graph_facts ──► GraphFacts
"""

from __future__ import annotations

import json
from bisect import bisect_right
from collections.abc import Iterable, Sequence

from maxitor.graph_builder.schemas import GraphRefused, check_graph
from maxitor.repo_graph_port.graph_facts import GraphFacts
from maxitor.repo_graph_port.tag import Tag


def place_tags(chain: Sequence[str], versions: Sequence[str], tags: Iterable[Tag]) -> dict[str, list[str]]:
    """
    AI-CORE-BEGIN
    ROLE: Put each tag on the version it belongs to.
    CONTRACT: ``chain`` is the branch's first-parent commits, oldest first; ``versions`` are those of them that changed the graph file. Returns version sha → tag names, sorted; a tag whose commit is not on ``chain``, or comes before the first version, is left out.
    AI-CORE-END
    """
    position = {sha: index for index, sha in enumerate(chain)}
    on_chain = sorted((position[sha], sha) for sha in versions if sha in position)
    indexes = [index for index, _ in on_chain]
    placed: dict[str, list[str]] = {}
    for tag in tags:
        where = position.get(tag.sha)
        if where is None:
            continue
        newest = bisect_right(indexes, where) - 1
        if newest < 0:
            continue
        placed.setdefault(on_chain[newest][1], []).append(tag.name)
    return {sha: sorted(names) for sha, names in placed.items()}


def graph_facts(content: bytes) -> GraphFacts:
    """
    AI-CORE-BEGIN
    ROLE: Say what a version's file is: a graph with its counts, or refused with the reason.
    CONTRACT: Never raises for any bytes; a file that is not JSON or fails the protocol's schema of the version it claims is ``refused``.
    AI-CORE-END
    """
    try:
        document = json.loads(content)
    except ValueError as error:
        return GraphFacts(nodes=None, edges=None, refused=f"not JSON: {error}")
    try:
        check_graph(document)
    except GraphRefused as refused:
        return GraphFacts(nodes=None, edges=None, refused=str(refused))
    return GraphFacts(nodes=len(document["nodes"]), edges=len(document["edges"]), refused=None)
