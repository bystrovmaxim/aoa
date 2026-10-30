# packages/maxitor/front/src/maxitor/front/api/access_log.py
"""
Access log — uvicorn's request lines without a query.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

uvicorn writes every request line it serves, query included, and Maxitor's queries name
sources — whole addresses (spec 037, FR-011). The filter below rewrites each access line
to its method, path and status before it is written: an operator still sees that the
server serves, and no address reaches the log.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    uvicorn.access record (client, method, full path, http version, status)
        ──WithoutQuery──► (client, method, path without "?…", http version, status)
"""

from __future__ import annotations

import logging


class WithoutQuery(logging.Filter):
    """
    AI-CORE-BEGIN
    ROLE: Cut the query off every request line uvicorn's access logger writes.
    CONTRACT: Leaves every record through, its path argument cut at the first ``?``.
    AI-CORE-END
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Cut the query off the record's path, when it has the access log's five arguments."""
        if isinstance(record.args, tuple) and len(record.args) == 5:
            client, method, path, version, status = record.args
            record.args = (client, method, str(path).split("?", 1)[0], version, status)
        return True


def install() -> None:
    """Install the filter on uvicorn's access logger, once."""
    logger = logging.getLogger("uvicorn.access")
    if not any(isinstance(existing, WithoutQuery) for existing in logger.filters):
        logger.addFilter(WithoutQuery())
