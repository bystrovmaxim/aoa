# packages/maxitor-gnomon/src/maxitor_gnomon/shipped.py
"""
Read a file the package ships beside its code: the protocol or a skill.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The Open Gnomon Protocol (``protocol/``) and the skills (``skills/``) sit at the
package's top level, not inside the code: the standard comes first, and this
package is one implementation of it. The code reads them through this module.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

An installed wheel carries both folders inside ``maxitor_gnomon/`` (hatch's
``force-include``); an editable install, as in this repository's workspace,
points at ``src/`` and leaves them where they are, two folders up. A file is
read from the first of those two places that has it.
"""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path

# ``packages/maxitor-gnomon/`` in a source checkout: ``src/maxitor_gnomon/shipped.py`` is two folders down.
_SOURCE_ROOT = Path(__file__).resolve().parents[2]


def shipped_text(*parts: str) -> str:
    """
    AI-CORE-BEGIN
    ROLE: The text of a shipped file, e.g. ``shipped_text("protocol", "graph", "1.1.json")``.
    CONTRACT: Reads the installed copy inside ``maxitor_gnomon/``, else the source tree's; raises ``FileNotFoundError`` when neither has it.
    AI-CORE-END
    """
    installed = files("maxitor_gnomon").joinpath(*parts)
    if installed.is_file():
        return installed.read_text(encoding="utf-8")
    return _SOURCE_ROOT.joinpath(*parts).read_text(encoding="utf-8")
