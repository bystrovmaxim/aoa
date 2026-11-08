# tests/scripts/test_no_renamed_class_names.py
"""No page, README or docstring names a class by the name the naming rules took from it — except history."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# The "Before" column of "Classes renamed by the naming rules" in docs/reference/intents-and-invariants.md.
# ``Plugin`` is also the suffix every plugin ends with, so it counts only where it stands for the base class:
# imported, inherited from, or written as a type (``list[Plugin]``, ``plugin: Plugin``); a diagram's ``[Plugin]`` box is a role.
RENAMED = re.compile(
    r"\b(?:SqlResource|PostgresResource|WrapperSqlResource|ParamsStub|ResultStub|SocketChannel"
    r"|WrapperLangGraphController|OcelStoreResource|InMemoryOcelStoreResource|OcelStoreWrapper)\b"
    r"|\bimport Plugin\b|\(Plugin[)\[,]|(?<=\w)\[Plugin\]|: Plugin\b"
)
TEXT_FILES = (".md", ".py", ".ipynb")
RENAMING_TABLE = "docs/reference/intents-and-invariants.md"
# This test and the test that the stub names are gone name the old names to find them.
NAMING_THEM = {"tests/scripts/test_no_renamed_class_names.py", "packages/aoa-action-machine/tests/action_machine/model/test_payload_naming.py"}


def _kept_as_history(path: str) -> bool:
    """Specs and changelogs keep the names they were written with."""
    return path.startswith("specs/") or Path(path).name.startswith("CHANGELOG") or path in NAMING_THEM


def _is_renaming_row(path: str, line: str) -> bool:
    """A row of the renaming table names the old class beside the new one."""
    return path == RENAMING_TABLE and line.startswith("| `") and " | `" in line and "Before" not in line


def test_no_page_names_a_renamed_class() -> None:
    """Every file outside history names ``SqlStorage``, ``BasePlugin``, ``StubParams`` and the rest by their new names."""
    listed = subprocess.run(["git", "ls-files", "-z"], check=True, capture_output=True, cwd=REPO_ROOT).stdout
    found: list[str] = []
    for path in filter(None, listed.decode().split("\0")):
        if not path.endswith(TEXT_FILES) or _kept_as_history(path) or not (REPO_ROOT / path).is_file():
            continue
        text = (REPO_ROOT / path).read_text(encoding="utf-8", errors="ignore")
        for match in RENAMED.finditer(text):
            line = text[text.rfind("\n", 0, match.start()) + 1 : text.find("\n", match.end())]
            if not _is_renaming_row(path, line):
                found.append(f"{path}:{text.count(chr(10), 0, match.start()) + 1}: {match.group()}")
    assert found == [], "renamed classes still named:\n" + "\n".join(found[:20])
