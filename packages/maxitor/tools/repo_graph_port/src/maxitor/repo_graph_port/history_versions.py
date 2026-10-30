# packages/maxitor/tools/repo_graph_port/src/maxitor/repo_graph_port/history_versions.py
"""
The rules of a history: where a tag lands, and what a version's file says.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Three decisions every reader of a history must make the same way. A tag is placed
on the newest version whose commit is an ancestor-or-self of the tag's commit on
the branch's first-parent chain — so a tag on a later commit that did not change
the graph lands on the version before it, and a tag off that chain is not placed.
A version's file is a graph, counted, or it is refused with the protocol's reason.
A version made by merging a pull request names it in its message — GitHub's merge
commit ("Merge pull request #147 from …", then the title and the description) or
its squash commit ("Title (#147)", then the description) — so a history whose
host does not tell pull requests (a local repository) still has them.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

Pure functions, no I/O: the mirror reads, these decide.

::

    first-parent chain + version shas + tags ──► place_tags ──► {version sha: tag names}
    a version's file bytes                   ──► graph_facts ──► GraphFacts
    a version's commit message               ──► pull_request_in_message ──► number, title, body, url | None
    the graph before + the graph after       ──► graph_change ──► nodes added and removed by kind, changed; links added and removed
"""

from __future__ import annotations

import json
import re
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


_MERGE = re.compile(r"^Merge pull request #(\d+) from \S+[ \t]*$")
_SQUASH = re.compile(r"^(.+?) \(#(\d+)\)[ \t]*$")


def pull_request_in_message(message: str, pull_url: str) -> dict[str, str | int] | None:
    """
    AI-CORE-BEGIN
    ROLE: Find the pull request a version's commit message says it merged.
    CONTRACT: A GitHub merge commit ("Merge pull request #N from <branch>", a blank line, the title, a blank line, the description) or a squash commit (first line "<title> (#N)", a blank line, the description) gives number, title, body and url — ``pull_url`` with the number appended, or "" when ``pull_url`` is ""; any other message gives ``None``. The merge line itself is never part of the title or body.
    AI-CORE-END
    """
    lines = message.strip("\n").split("\n")
    merge = _MERGE.match(lines[0])
    if merge:
        rest = "\n".join(lines[1:]).strip("\n").split("\n")
        number, title, body = int(merge.group(1)), rest[0].strip(), "\n".join(rest[1:]).strip("\n")
    else:
        squash = _SQUASH.match(lines[0])
        if not squash:
            return None
        number, title, body = int(squash.group(2)), squash.group(1).strip(), "\n".join(lines[1:]).strip("\n")
    return {"number": number, "title": title, "body": body, "url": f"{pull_url}{number}" if pull_url else ""}


def graph_change(before: bytes | None, after: bytes) -> dict[str, object]:
    """
    AI-CORE-BEGIN
    ROLE: Say what a version did to the graph of the version before it.
    CONTRACT: Nodes are matched by ``id``: ``added`` and ``removed`` count them by ``type``; ``changed`` counts nodes kept whose type, label or properties differ. Edges — the links between nodes — are matched by ``id`` (or source, relationship and target when they have none): ``links`` counts those ``added`` and ``removed``. ``before`` is ``None`` for the first version, whose every node and edge is added. A file that is not a graph counts as having none; never raises.
    AI-CORE-END
    """
    old, new = _nodes(before), _nodes(after)
    added: dict[str, int] = {}
    removed: dict[str, int] = {}
    for key in new.keys() - old.keys():
        kind = str(new[key].get("type", "node"))
        added[kind] = added.get(kind, 0) + 1
    for key in old.keys() - new.keys():
        kind = str(old[key].get("type", "node"))
        removed[kind] = removed.get(kind, 0) + 1
    changed = sum(1 for key in new.keys() & old.keys() if new[key] != old[key])
    old_links, new_links = _edges(before), _edges(after)
    links = {"added": len(new_links - old_links), "removed": len(old_links - new_links)}
    return {"added": dict(sorted(added.items())), "removed": dict(sorted(removed.items())), "changed": changed, "links": links}


def _edges(content: bytes | None) -> set[str]:
    """A graph file's edges, each by its id, or by source, relationship and target; anything that is not a graph has none."""
    if not content:
        return set()
    try:
        edges = json.loads(content).get("edges", [])
    except (ValueError, AttributeError):
        return set()
    return {
        str(edge.get("id") or f"{edge.get('source_id')}|{edge.get('relationship')}|{edge.get('target_id')}")
        for edge in edges
        if isinstance(edge, dict)
    }


def _nodes(content: bytes | None) -> dict[str, dict[str, object]]:
    """A graph file's nodes by id; anything that is not a graph has none."""
    if not content:
        return {}
    try:
        nodes = json.loads(content).get("nodes", [])
    except (ValueError, AttributeError):
        return {}
    return {str(node["id"]): node for node in nodes if isinstance(node, dict) and "id" in node}
