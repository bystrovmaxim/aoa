# tests/examples/test_page_blocks.py
"""
Every Python block of a page runs as written, or says why it does not.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A reader copies a block from a page. A block whose first line is
``# Fragment: <reason>.`` is a part shown on its own and is not run; every other
Python block runs after the earlier unmarked blocks of its page, in one process
from the repository root. When the page shows what a block prints, in a ``text``
block right after it, the block prints exactly that once the values that differ
on every run are masked.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.examples.harness import REPO_ROOT, mask, page_blocks, pages_in_scope, run_page

_PAGES = [page for page in pages_in_scope() if any(block.language == "python" for block in page_blocks(page))]


def _page_id(page: Path) -> str:
    return page.relative_to(REPO_ROOT).as_posix()


@pytest.mark.parametrize("page", _PAGES, ids=_page_id)
def test_every_fragment_says_why(page: Path) -> None:
    unexplained = [block.where for block in page_blocks(page) if block.language == "python" and block.fragment_reason == ""]
    assert not unexplained, f"fragment marks without a reason: {unexplained}"


@pytest.mark.parametrize("page", _PAGES, ids=_page_id)
def test_every_unmarked_block_runs_and_prints_what_the_page_shows(page: Path) -> None:
    blocks = [block for block in page_blocks(page) if block.language == "python" and block.fragment_reason is None]
    if not blocks:
        return
    for run in run_page(blocks):
        assert run.error is None, f"{run.block.where} does not run:\n{run.error}"
        if run.block.shown_output is not None:
            assert mask(run.printed) == mask(run.block.shown_output), (
                f"{run.block.where} prints something else than the page shows\n"
                f"--- the page shows ---\n{run.block.shown_output}\n--- it prints ---\n{run.printed}"
            )
