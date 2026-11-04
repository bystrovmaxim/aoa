# tests/examples/test_harness.py
"""
Tests of the example harness: blocks, fragment marks, shown outputs, masking, page runs.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.examples.harness import REPO_ROOT, mask, page_blocks, pages_in_scope, run_page


def _page(tmp_path: Path, text: str) -> Path:
    """Write ``text`` as a page in ``tmp_path``."""
    page = tmp_path / "page.md"
    page.write_text(text, encoding="utf-8")
    return page


def test_fragment_reason_is_read_from_the_first_line(tmp_path: Path) -> None:
    page = _page(tmp_path, "```python\n# Fragment: one method of an action.\ndef run(self): ...\n```\n")
    (block,) = page_blocks(page)
    assert block.fragment_reason == "one method of an action."


def test_a_block_without_the_mark_has_no_reason(tmp_path: Path) -> None:
    page = _page(tmp_path, "```python\nprint(1)\n```\n")
    (block,) = page_blocks(page)
    assert block.fragment_reason is None


def test_an_empty_reason_is_read_as_empty(tmp_path: Path) -> None:
    page = _page(tmp_path, "```python\n# Fragment:\nx\n```\n")
    (block,) = page_blocks(page)
    assert block.fragment_reason == ""


def test_shown_output_follows_directly(tmp_path: Path) -> None:
    page = _page(tmp_path, "```python\nprint(1)\n```\n\n```text\n1\n```\n")
    assert page_blocks(page)[0].shown_output == "1\n"


def test_shown_output_follows_a_lead_in_ending_with_a_colon(tmp_path: Path) -> None:
    page = _page(tmp_path, "```python\nprint(1)\n```\n\nIt prints:\n\n```text\n1\n```\n")
    assert page_blocks(page)[0].shown_output == "1\n"


def test_a_block_with_no_language_is_a_shown_output(tmp_path: Path) -> None:
    page = _page(tmp_path, "```python\nprint(1)\n```\n\n```\n1\n```\n")
    assert page_blocks(page)[0].shown_output == "1\n"


def test_other_prose_breaks_the_pair(tmp_path: Path) -> None:
    page = _page(tmp_path, "```python\nprint(1)\n```\n\nA layout of folders.\n\n```text\na/\n```\n")
    assert page_blocks(page)[0].shown_output is None


def test_an_indented_block_loses_its_indent(tmp_path: Path) -> None:
    page = _page(tmp_path, "1. Step:\n\n   ```python\n   x = 1\n   ```\n")
    assert page_blocks(page)[0].code == "x = 1\n"


@pytest.mark.parametrize(
    ("raw", "masked"),
    [
        ("https://errors.pydantic.dev/2.12/v/value_error", "https://errors.pydantic.dev/<v>/v/value_error"),
        ("id 1b0a9e3d-4dde-50d2-a421-1c7b1e2d78a1", "id <uuid>"),
        ("sid 1ac03e1742124bb5acbd33c2444dda3f", "sid <hex>"),
        ("at 0x10a2b3c4d", "at <addr>"),
        ("at 2026-11-04T03:00:00.123+00:00", "at <time>"),
        ("took 0.61 ms", "took <duration>"),
        ("http://127.0.0.1:60780/x", "http://127.0.0.1:<port>/x"),
        ("token eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJhIn0.c2ln", "token <jwt>"),
        ("on_cache_write: duration_ms=81.5, write=yes", "on_cache_write: duration_ms=<n>, write=yes"),
        ('"aoa.duration_ms": 0.0290870666', '"aoa.duration_ms": <n>'),
        ("'iat': 1793750449", "'iat': <epoch>"),
        ("order_id: ord-1dc8d4c0", "order_id: ord-<id>"),
        ("order_id: ord-25776620", "order_id: ord-<id>"),
        ("item ord-deadbeef", "item ord-deadbeef"),
        ("kept 42   ", "kept 42"),
    ],
)
def test_mask_replaces_values_that_differ_on_every_run(raw: str, masked: str) -> None:
    assert mask(raw) == masked


def test_a_later_block_sees_an_earlier_blocks_names(tmp_path: Path) -> None:
    page = _page(tmp_path, "```python\nx = 41\n```\n\n```python\nprint(x + 1)\n```\n")
    runs = run_page(page_blocks(page))
    assert [run.error for run in runs] == [None, None]
    assert runs[1].printed == "42\n"


def test_postponed_annotations_resolve(tmp_path: Path) -> None:
    code = "from __future__ import annotations\nfrom pydantic import BaseModel\nclass A(BaseModel):\n    b: B | None = None\nclass B(BaseModel):\n    x: int = 1\nA.model_rebuild()\nprint(A(b=B()).b.x)\n"
    page = _page(tmp_path, "```python\n" + code + "```\n")
    (run,) = run_page(page_blocks(page))
    assert run.error is None and run.printed == "1\n"


def test_a_whole_module_runs_alone(tmp_path: Path) -> None:
    page = _page(tmp_path, "```python\nx = 1\n```\n\n```python\n\"\"\"A module.\"\"\"\nprint('x' in globals())\n```\n")
    runs = run_page(page_blocks(page))
    assert [run.error for run in runs] == [None, None] and runs[1].printed == "False\n"


def test_top_level_await_runs(tmp_path: Path) -> None:
    page = _page(tmp_path, "```python\nimport asyncio\nawait asyncio.sleep(0)\nprint('done')\n```\n")
    (run,) = run_page(page_blocks(page))
    assert run.error is None and run.printed == "done\n"


def test_a_failing_block_stops_the_page(tmp_path: Path) -> None:
    page = _page(tmp_path, "```python\nraise ValueError('no')\n```\n\n```python\nprint(1)\n```\n")
    runs = run_page(page_blocks(page))
    assert len(runs) == 1 and "ValueError: no" in (runs[0].error or "")


def test_pages_in_scope_are_tracked_pages_a_reader_opens() -> None:
    pages = {page.relative_to(REPO_ROOT).as_posix() for page in pages_in_scope()}
    assert "README.md" in pages
    assert "docs/tutorials/step-01-action-and-pipeline.md" in pages
    assert not any(name.endswith("_draft.md") or "CHANGELOG" in name for name in pages)
    assert not any("node_modules" in name for name in pages)
