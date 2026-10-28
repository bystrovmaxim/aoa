# packages/maxitor/src/maxitor/__init__.py
"""
maxitor — the AOA system viewer and its tools, one package with extras.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Maxitor is installed once and its parts are chosen at install time:
``maxitor.viewer`` (the server and its built front) comes with the extra
``viewer``. This module holds the version and imports nothing, so a part can be
used without the others' dependencies.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

Each part is a subpackage with its own allowed imports, checked by
``scripts/check_package_boundaries.py``. ``maxitor.launch`` starts a part from
its command and names the extra when the part's dependencies are missing.
"""

from __future__ import annotations

__version__ = "3.0.0"

__all__ = ["__version__"]
