# packages/maxitor/front/src/maxitor/front/model/core/freshness.py
"""
When a held graph is due for a check, and when a tab counts as open (spec 028, FR-071, FR-073).

A source that gives ``ETag`` or ``Last-Modified`` is cheap to ask — an unchanged one answers
``304`` — so it is asked every 30 seconds; one that gives neither is downloaded whole to compare
hashes, so every 2 minutes. A tab outside a room asks for the fingerprint every 30 seconds, so a
source last asked about more than 75 seconds ago has no open tab left: two missed polls and a margin.
"""

from __future__ import annotations

from maxitor.front.api.graph_store import GraphEntry

#: Seconds between checks of a source that gives validators.
CHECK_WITH_VALIDATORS_SECONDS = 30.0
#: Seconds between checks of a source that gives none.
CHECK_WITHOUT_VALIDATORS_SECONDS = 120.0
#: Seconds since a tab last asked, after which it no longer counts as open.
OPEN_TAB_SECONDS = 75.0


def check_interval(entry: GraphEntry) -> float:
    """How often ``entry``'s source is checked."""
    return CHECK_WITH_VALIDATORS_SECONDS if entry.etag or entry.last_modified else CHECK_WITHOUT_VALIDATORS_SECONDS


def is_due(entry: GraphEntry, now: float) -> bool:
    """Whether ``entry``'s source is due for a check at ``now``, and none is running."""
    return not entry.checking and now - entry.last_checked >= check_interval(entry)


def tab_is_open(last_seen: float | None, now: float) -> bool:
    """Whether a tab that last asked at ``last_seen`` still counts as open at ``now``."""
    return last_seen is not None and now - last_seen <= OPEN_TAB_SECONDS
