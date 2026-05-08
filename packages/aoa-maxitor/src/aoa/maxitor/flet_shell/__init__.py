# packages/aoa-maxitor/src/aoa/maxitor/flet_shell/__init__.py
"""
Flet shell — optional desktop host for Maxitor HTML viewers.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Holds the Flet application scaffold (navigation + workspace) that loads the
interchange graph and ERD HTML exports. Install with the ``flet`` extra:
``aoa-maxitor[flet]``.

═══════════════════════════════════════════════════════════════════════════════
RUN
═══════════════════════════════════════════════════════════════════════════════

``python -m aoa.maxitor.flet_shell`` (after installing ``aoa-maxitor[flet]``), or the
``maxitor-flet`` console script from the same extra. For the same UI in your system
browser, set ``MAXITOR_FLET_WEB=1`` (see ``__main__.run``).
"""

from __future__ import annotations

__all__: list[str] = []
