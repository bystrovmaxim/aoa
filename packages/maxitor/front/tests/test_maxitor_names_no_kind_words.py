# tests/maxitor/test_maxitor_names_no_kind_words.py
"""
Tests that Maxitor names no entity kind word outside its icon dictionary.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The kinds a viewer shows and what they are called come from the graph. The only
place in Maxitor allowed to name AOA's kind words is the client's icon dictionary
(``client/src/lib/icons/entity_kind_glyphs.ts``), which decides pictures and nothing
else. This scan fails on a kind word compared with, or keyed by, an entity kind
anywhere else — the way ``entity.get("entity_kind") == "enum"`` once chose which
cards are dictionaries.
"""

from __future__ import annotations

import re
from pathlib import Path

_PACKAGE = Path(__file__).resolve().parents[1]
_ALLOWED = _PACKAGE / "client/src/lib/icons/entity_kind_glyphs.ts"
_WORDS = ("core", "assoc", "detail", "spec", "enum", "state")
_WORD = "|".join(_WORDS)
# A kind word used as a kind: compared with ``entity_kind`` (either side) on one line.
_KIND_USE = re.compile(
    rf"""entity_kind\W[^\n]{{0,40}}?(?:==|!=|===|!==)\s*["']({_WORD})["']"""
    rf"""|["']({_WORD})["']\s*(?:==|!=|===|!==)[^\n]{{0,40}}?entity_kind"""
)


def _sources() -> list[Path]:
    """Maxitor's own server and client sources, built assets excluded."""
    server = [p for p in (_PACKAGE / "src/maxitor/front").rglob("*.py") if "static" not in p.parts]
    client = [p for p in (_PACKAGE / "client/src").rglob("*") if p.suffix in {".ts", ".tsx"} and ".test." not in p.name]
    return server + client


def test_no_source_names_a_kind_word_as_a_kind() -> None:
    """The filter, the names and the listing are derived from the graph, never from a word in the code."""
    found = []
    for path in _sources():
        if path == _ALLOWED:
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if _KIND_USE.search(line):
                found.append(f"{path.relative_to(_PACKAGE)}:{number}: {line.strip()}")
    assert found == []


def test_the_scan_sees_the_pattern_it_guards_against() -> None:
    """The rule catches the line that used to choose dictionary cards by the word ``enum``."""
    assert _KIND_USE.search('            if entity.get("entity_kind") == "enum":')
    assert _KIND_USE.search('if (nd.entity_kind === "core") {')
    assert not _KIND_USE.search('if entity.pop("declares_values"):')
