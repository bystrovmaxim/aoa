# packages/maxitor/front/src/maxitor/front/model/core/source_label.py
"""
Source labels — name an address in a log or an error without showing it.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

An address may carry what must not be written down — a query with a link, a path a
service would rather keep — and a log or an error text is read by more people than the
address was given to (spec 037, FR-011, FR-011a). A source is therefore named by its
origin, which says which service a line is about, and the first 8 hex characters of the
SHA-256 of the whole address, which tell two addresses of one origin apart.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    "https://dev.demo.aoa.run/examples/model/graph-json" ──label()──► "https://dev.demo.aoa.run#3f9a1c2b"
"""

from __future__ import annotations

import hashlib
from urllib.parse import urlsplit


def label(address: str) -> str:
    """
    AI-CORE-BEGIN
    ROLE: The one way an address is named in a log line or an error text.
    CONTRACT: Returns ``<scheme>://<host[:port]>#<first 8 hex of SHA-256 of the whole address>``; an address with no origin is named ``source#<hash>``.
    INVARIANTS: Never returns the user, the password, the path, the query or the fragment of ``address``.
    AI-CORE-END
    """
    digest = hashlib.sha256(address.encode("utf-8")).hexdigest()[:8]
    parts = urlsplit(address.strip())
    # Whatever stands before ``@`` is a user and password; the origin never carries them.
    host = parts.netloc.rsplit("@", 1)[-1]
    if not parts.scheme or not host:
        return f"source#{digest}"
    return f"{parts.scheme}://{host}#{digest}"
