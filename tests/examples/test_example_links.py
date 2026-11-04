# tests/examples/test_example_links.py
"""
Every link from a page to an example leads to it, and every Colab button opens the repository's notebook.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A relative link to a file under ``examples/`` resolves to a file that exists. A
link whose text names Colab is
``https://colab.research.google.com/github/bystrovmaxim/aoa/blob/main/<path>.ipynb``
for a notebook that exists, so Colab opens the repository's own notebook in its
current version and no copy kept elsewhere drifts from it.
"""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote

import pytest

from tests.examples.harness import REPO_ROOT, pages_in_scope

COLAB_PREFIX = "https://colab.research.google.com/github/bystrovmaxim/aoa/blob/main/"
_LINK = re.compile(r"\[(?P<text>[^\]]*)\]\((?P<target>[^)\s]+)\)")


def _page_id(page: Path) -> str:
    return page.relative_to(REPO_ROOT).as_posix()


def _links(page: Path) -> list[tuple[int, str, str]]:
    """Links of ``page`` outside code blocks, as (line, text, target)."""
    found = []
    in_code = False
    for number, line in enumerate(page.read_text(encoding="utf-8").splitlines(), start=1):
        if line.lstrip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        found.extend((number, match.group("text"), match.group("target")) for match in _LINK.finditer(line))
    return found


@pytest.mark.parametrize("page", pages_in_scope(), ids=_page_id)
def test_links_to_examples_lead_to_them(page: Path) -> None:
    broken = []
    for number, text, target in _links(page):
        if "colab" in text.lower():
            path = target.removeprefix(COLAB_PREFIX)
            if not target.startswith(COLAB_PREFIX) or not path.endswith(".ipynb") or not (REPO_ROOT / path).is_file():
                broken.append(f"{_page_id(page)}:{number} Colab button {target}")
            continue
        if target.startswith(("http:", "https:", "mailto:", "#")):
            continue
        relative = unquote(target.split("#")[0])
        resolved = (page.parent / relative).resolve()
        if "examples" in Path(relative).parts and not resolved.exists():
            broken.append(f"{_page_id(page)}:{number} {target}")
    assert not broken, "links that lead nowhere:\n" + "\n".join(broken)
