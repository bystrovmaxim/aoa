# packages/maxitor/tools/graph_builder/src/maxitor/graph_builder/differences.py
"""
Name what changed between two graph documents, by ``id``.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

When a saved graph is stale, a person needs to see what moved, not a text diff
of thousands of lines. Nodes and edges carry an ``id``, so an element is matched
by it wherever it sits in the file, and each change is one line.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    old, new ──► maxitor.graph_compare.compare ──► one line per element added or removed,
                                                   one per property of a changed one
             └─ the other top-level keys (``schema_version``) ──► walked as plain JSON
             └─ a document compare refuses ──► the whole of it walked as plain JSON

The comparison itself is ``maxitor.graph_compare``'s, the one Maxitor draws from:
a ``1.0`` graph's edges get their ids by #285's rule. Only a document that cannot be
compared — a broken file ``check`` still has to explain — falls back to a generic walk:
objects key by key, an array whose items all carry an ``id`` by ``id``, anything else
by equality.
"""

from __future__ import annotations

import json
from collections.abc import Iterator, Mapping
from typing import Any

from maxitor.graph_compare import Change, Comparison, GraphNotComparableError, Status, compare

SHOWN_CHARACTERS = 60

_ELEMENTS = ("nodes", "edges")
"""The top-level keys whose items the comparison matches by id."""


def _shown(value: Any) -> str:
    """A value as one short line: text as it is, anything else as JSON."""
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, sort_keys=True)
    return text if len(text) <= SHOWN_CHARACTERS else text[: SHOWN_CHARACTERS - 1] + "…"


def _by_id(items: list[Any]) -> dict[str, Any] | None:
    """The items keyed by ``id`` when every item is an object with its own ``id``; otherwise ``None``."""
    keyed: dict[str, Any] = {}
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str) or item["id"] in keyed:
            return None
        keyed[item["id"]] = item
    return keyed


def _walk(old: Any, new: Any, path: str) -> Iterator[str]:
    """Every difference under ``path``, one line each, in a stable order — for what the comparison does not read."""
    if isinstance(old, dict) and isinstance(new, dict):
        for key in sorted(old.keys() | new.keys()):
            inner = f"{path}.{key}" if path else key
            if key not in new:
                yield f"{inner}: removed"
            elif key not in old:
                yield f"{inner}: added"
            else:
                yield from _walk(old[key], new[key], inner)
        return
    if isinstance(old, list) and isinstance(new, list):
        old_ids, new_ids = _by_id(old), _by_id(new)
        if old_ids is not None and new_ids is not None:
            for item_id in [*old_ids, *(i for i in new_ids if i not in old_ids)]:
                inner = f"{path}[id={item_id}]"
                if item_id not in new_ids:
                    yield f"{inner}: removed"
                elif item_id not in old_ids:
                    yield f"{inner}: added"
                else:
                    yield from _walk(old_ids[item_id], new_ids[item_id], inner)
            return
    if old != new:
        yield f"{path}: {_shown(old)} → {_shown(new)}"


def _compared(comparison: Comparison, kind: str) -> Iterator[str]:
    """One kind's lines from the comparison: an element added or removed, or each changed property by its path."""
    for element_id, item in (comparison.nodes if kind == "nodes" else comparison.edges).items():
        head = f"{kind}[id={element_id}]"
        if item.status is Status.ADDED or item.status is Status.REMOVED:
            yield f"{head}: {item.status.value}"
        for difference in item.differences:
            path = head + "".join(f".{key}" for key in difference.path)
            if difference.change is Change.CHANGED:
                yield f"{path}: {_shown(difference.before)} → {_shown(difference.after)}"
            else:
                yield f"{path}: {difference.change.value}"


def _lines(old: Any, new: Any) -> Iterator[str]:
    """Every line, top-level keys in order: nodes and edges from the comparison, the rest walked."""
    if not (isinstance(old, Mapping) and isinstance(new, Mapping)):
        yield from _walk(old, new, "")
        return
    try:
        comparison = compare(old, new)
    except GraphNotComparableError:
        yield from _walk(old, new, "")
        return
    for key in sorted(old.keys() | new.keys()):
        if key in _ELEMENTS:
            yield from _compared(comparison, key)
        elif key not in new:
            yield f"{key}: removed"
        elif key not in old:
            yield f"{key}: added"
        else:
            yield from _walk(old[key], new[key], key)


def differences(old: Any, new: Any, limit: int = 20) -> list[str]:
    """
    AI-CORE-BEGIN
    ROLE: The differences between two graph documents, one line each, elements matched by ``id``.
    CONTRACT: Returns ``[]`` when the documents are equal; otherwise at most ``limit`` lines, then ``… and N more``.
    AI-CORE-END
    """
    lines = list(_lines(old, new))
    if len(lines) > limit:
        return [*lines[:limit], f"… and {len(lines) - limit} more"]
    return lines
