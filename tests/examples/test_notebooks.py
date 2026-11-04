# tests/examples/test_notebooks.py
"""
Every notebook of ``examples/`` installs what it imports, runs, and prints its script's lines.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A notebook is the same case as its script, step by step, and it opens in Colab
from the repository. Its first code cell installs, by PyPI name, every package
its imports need. It runs from its first cell to its last in a fresh kernel in
its own folder, with the install cell skipped because the repository's
environment already holds the packages. Every line it prints is a line its
script prints, in the same order, once the values that differ on every run are
masked; a notebook may leave out the headings its Markdown cells say instead.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import nbformat
import pytest
from nbclient import NotebookClient

from tests.examples.harness import (
    EXAMPLES_ROOT,
    REPO_ROOT,
    imported_modules,
    installed_requirements,
    is_satisfied,
    mask,
    requirements_for,
)
from tests.examples.test_examples_run import _SCRIPTS

_TIMEOUT_SECONDS = 120

_NOTEBOOKS = sorted(path for path in EXAMPLES_ROOT.rglob("*.ipynb") if ".ipynb_checkpoints" not in path.parts)


def _example_id(path: Path) -> str:
    return path.relative_to(EXAMPLES_ROOT).as_posix()


def _code_cells(notebook: nbformat.NotebookNode) -> list[nbformat.NotebookNode]:
    return [cell for cell in notebook.cells if cell.cell_type == "code"]


def _is_install_cell(cell: nbformat.NotebookNode) -> bool:
    return cell.source.lstrip().startswith("!pip install")


def _local_modules(notebook_path: Path, notebook: nbformat.NotebookNode) -> set[str]:
    """Top-level names a notebook can import from its own folder or from files it writes."""
    names = {path.stem for path in notebook_path.parent.glob("*.py")}
    names |= {path.parent.name for path in notebook_path.parent.glob("*/__init__.py")}
    for cell in _code_cells(notebook):
        first = cell.source.lstrip().splitlines()[0] if cell.source.strip() else ""
        if first.startswith("%%writefile"):
            names.add(first.split()[-1].split("/")[0].removesuffix(".py"))
    return names


def _printed_lines(text: str) -> list[str]:
    """Masked printed lines without their indent, which a notebook drops with a script's headings."""
    return [line.strip() for line in mask(text).splitlines() if line.strip()]


def test_every_script_has_a_notebook() -> None:
    missing = [_example_id(script) for script in _SCRIPTS if not script.with_suffix(".ipynb").exists()]
    assert not missing, f"scripts without a notebook: {missing}"


@pytest.mark.parametrize("notebook_path", _NOTEBOOKS, ids=_example_id)
def test_notebook_installs_what_it_imports(notebook_path: Path) -> None:
    notebook = nbformat.read(notebook_path, as_version=4)
    cells = _code_cells(notebook)
    assert cells and _is_install_cell(cells[0]), f"{_example_id(notebook_path)}: the first code cell is not `!pip install …`"
    installed = installed_requirements(cells[0].source.strip().splitlines()[0])
    local = _local_modules(notebook_path, notebook)
    missing: list[str] = []
    for module in sorted(imported_modules([cell.source for cell in cells[1:]])):
        if module.split(".")[0] in local:
            continue
        needed = requirements_for(module)
        if needed is None:
            missing.append(f"{module} (no PyPI package known for it)")
            continue
        missing.extend(f"{module} needs {requirement}" for requirement in needed if not is_satisfied(requirement, installed))
    assert not missing, f"{_example_id(notebook_path)}: the install cell leaves out: {missing}"


@pytest.mark.parametrize("notebook_path", _NOTEBOOKS, ids=_example_id)
def test_notebook_runs_and_prints_its_scripts_lines(notebook_path: Path) -> None:
    notebook = nbformat.read(notebook_path, as_version=4)
    notebook.cells = [cell for cell in notebook.cells if not (cell.cell_type == "code" and _is_install_cell(cell))]
    client = NotebookClient(
        notebook,
        timeout=_TIMEOUT_SECONDS,
        kernel_name="python3",
        resources={"metadata": {"path": str(notebook_path.parent)}},
    )
    client.execute()
    printed = "".join(
        output.get("text", "")
        for cell in _code_cells(notebook)
        for output in cell.get("outputs", [])
        if output.get("output_type") == "stream" and output.get("name") == "stdout"
    )
    script = notebook_path.with_suffix(".py")
    ran = subprocess.run(
        [sys.executable, str(script)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=_TIMEOUT_SECONDS,
        check=True,
    )
    script_lines = _printed_lines(ran.stdout)
    position = 0
    for line in _printed_lines(printed):
        try:
            position = script_lines.index(line, position) + 1
        except ValueError:
            pytest.fail(f"{_example_id(notebook_path)} prints a line its script does not, or out of order: {line!r}")
