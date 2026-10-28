# packages/maxitor-gnomon/src/maxitor_gnomon/shipped.py
"""
Read a file the package ships beside its code: a skill.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The skills (``skills/``) sit at the package's top level, not inside the code;
the code reads them through this module.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

An installed wheel carries the folder inside ``maxitor_gnomon/`` (hatch's
``force-include``); an editable install, as in this repository's workspace,
points at ``src/`` and leaves it where it is, two folders up. A file is
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
    ROLE: The text of a shipped file, e.g. ``shipped_text("skills", "gnomon-setup", "SKILL.md")``.
    CONTRACT: Reads the installed copy inside ``maxitor_gnomon/``, else the source tree's; raises ``FileNotFoundError`` when neither has it.
    AI-CORE-END
    """
    installed = files("maxitor_gnomon").joinpath(*parts)
    if installed.is_file():
        return installed.read_text(encoding="utf-8")
    return _SOURCE_ROOT.joinpath(*parts).read_text(encoding="utf-8")
